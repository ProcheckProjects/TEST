# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class TraitementPhysique(models.Model):
    _name = 'traitement.physique'
    _description = 'Traitement Physique des Dossiers Collecteurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'heure_debut desc'
    _rec_name = 'display_name'

    # === IDENTIFICATION ===
    dossier_id = fields.Many2one(
        'dossier.collecteur', 
        string='Dossier Collecteur', 
        required=True,
        ondelete='cascade',
        help="Dossier collecteur à traiter"
    )
    
    agent_id = fields.Many2one(
        'res.users', 
        string='Agent de Traitement', 
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=[("groups_id", "in", [lambda self: self.env.ref("archivage_secondv.group_agent_traitement").id])],
        help="Agent responsable du traitement physique"
    )
    
    # === INFORMATIONS DE TRAITEMENT ===
    radical_dossier = fields.Char(
        string='Radical Dossier', 
        required=True,
        tracking=True,
        help="Radical du dossier (identifiant principal)"
    )
    
    code_agence = fields.Char(
        string='Code Agence', 
        required=True,
        tracking=True,
        help="Code de l'agence d'origine (ex: 001, 002, etc.)"
    )
    
    # === GESTION DU TEMPS ===
    heure_debut = fields.Datetime(
        string='Heure de Début', 
        default=fields.Datetime.now,
        readonly=True,
        help="Heure de début du traitement (automatique)"
    )
    
    heure_fin = fields.Datetime(
        string='Heure de Fin', 
        readonly=True,
        help="Heure de fin du traitement (automatique)"
    )
    
    duree_traitement = fields.Float(
        string='Durée (minutes)', 
        compute='_compute_duree_traitement',
        store=True,
        readonly=True,
        help="Durée du traitement en minutes (calculée automatiquement)"
    )
    
    # === ÉTAT DU TRAITEMENT ===
    state = fields.Selection([
        ('en_cours', 'En Cours'),
        ('pause', 'En Pause'),
        ('termine', 'Terminé'),
        ('valide', 'Validé')
    ], string='État', default='en_cours', tracking=True, help="État actuel du traitement")
    
    nombre_pieces = fields.Integer(
        string='Nombre de Pièces',
        related='dossier_id.nombre_pieces',
        readonly=True,
        help='Nombre de pièces dans le dossier collecteur'
    )
    
    type_dossier = fields.Selection(
        related='dossier_id.type_dossier',
        readonly=True,
        help='Type de dossier collecteur'
    )
    nombre_pieces_traitees = fields.Integer(
        string='Nombre de Pièces Traitées',
        default=0,
        help="Nombre de pièces physiques traitées"
    )
    
    difficulte = fields.Selection([
        ('facile', 'Facile'),
        ('moyenne', 'Moyenne'),
        ('difficile', 'Difficile')
    ], string='Difficulté', default='moyenne', help="Niveau de difficulté du traitement")
    
    qualite_dossier = fields.Selection([
        ('excellent', 'Excellent'),
        ('bon', 'Bon'),
        ('moyen', 'Moyen'),
        ('mauvais', 'Mauvais')
    ], string='Qualité du Dossier', help="Évaluation de la qualité du dossier physique")
    
    # === PAUSES ET INTERRUPTIONS ===
    duree_pauses = fields.Float(
        string='Durée des Pauses (min)',
        default=0,
        help="Durée totale des pauses en minutes"
    )
    
    nombre_pauses = fields.Integer(
        string='Nombre de Pauses',
        default=0,
        help="Nombre de pauses effectuées"
    )
    
    heure_derniere_pause = fields.Datetime(
        string='Dernière Pause',
        help="Heure de la dernière pause"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes sur le traitement"
    )
    
    observations = fields.Text(
        string='Observations',
        help="Observations particulières sur le dossier"
    )
    
    problemes_rencontres = fields.Text(
        string='Problèmes Rencontrés',
        help="Description des problèmes rencontrés lors du traitement"
    )
    
    # === CHAMP D'AFFICHAGE ===
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True,
        help="Nom d'affichage du traitement"
    )
    
    # === MÉTRIQUES DE PERFORMANCE ===
    vitesse_traitement = fields.Float(
        string='Vitesse (pièces/min)',
        compute='_compute_vitesse_traitement',
        help="Vitesse de traitement en pièces par minute"
    )
    
    duree_effective = fields.Float(
        string='Durée Effective (min)',
        compute='_compute_duree_effective',
        help="Durée effective sans les pauses"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('heure_debut', 'heure_fin')
    def _compute_duree_traitement(self):
        for record in self:
            if record.heure_debut and record.heure_fin:
                delta = record.heure_fin - record.heure_debut
                record.duree_traitement = delta.total_seconds() / 60
            else:
                record.duree_traitement = 0
    
    @api.depends('duree_traitement', 'duree_pauses')
    def _compute_duree_effective(self):
        for record in self:
            record.duree_effective = record.duree_traitement - record.duree_pauses
    
    @api.depends('nombre_pieces_traitees', 'duree_effective')
    def _compute_vitesse_traitement(self):
        for record in self:
            if record.duree_effective > 0 and record.nombre_pieces_traitees > 0:
                record.vitesse_traitement = record.nombre_pieces_traitees / record.duree_effective
            else:
                record.vitesse_traitement = 0
    
    @api.depends('dossier_id')
    def _compute_display_name(self):
        for record in self:
            if record.dossier_id and record.radical_dossier:
                record.display_name = f"{record.dossier_id.numero_dossier} - {record.radical_dossier}"
            elif record.dossier_id:
                record.display_name = record.dossier_id.numero_dossier
            else:
                record.display_name = _('Nouveau traitement')
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        """Démarre automatiquement le chronomètre à la création"""
        if 'heure_debut' not in vals:
            vals['heure_debut'] = fields.Datetime.now()
        
        traitement = super(TraitementPhysique, self).create(vals)
        
        # Lier le traitement au dossier
        if traitement.dossier_id:
            traitement.dossier_id.traitement_id = traitement.id
        
        return traitement
    
    def write(self, vals):
        """Met à jour les informations du dossier lors de la modification"""
        result = super(TraitementPhysique, self).write(vals)
        
        # Mettre à jour le dossier collecteur si nécessaire
        for record in self:
            if 'radical_dossier' in vals or 'code_agence' in vals:
                record.dossier_id.write({
                    'radical_dossier': record.radical_dossier,
                    'code_agence': record.code_agence,
                    'agent_traitement_id': record.agent_id.id,
                    'observations_traitement': record.observations,
                })
        
        return result
    
    # === ACTIONS PRINCIPALES ===
    def action_mettre_en_pause(self):
        """Met le traitement en pause"""
        self.ensure_one()
        
        if self.state != 'en_cours':
            raise UserError(_("Seuls les traitements en cours peuvent être mis en pause."))
        
        self.write({
            'state': 'pause',
            'heure_derniere_pause': fields.Datetime.now(),
            'nombre_pauses': self.nombre_pauses + 1
        })
        
        self.message_post(
            body=_("Traitement mis en pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_reprendre_traitement(self):
        """Reprend le traitement après une pause"""
        self.ensure_one()
        
        if self.state != 'pause':
            raise UserError(_("Seuls les traitements en pause peuvent être repris."))
        
        if self.heure_derniere_pause:
            duree_pause = (fields.Datetime.now() - self.heure_derniere_pause).total_seconds() / 60
            self.duree_pauses += duree_pause
        
        self.write({
            'state': 'en_cours',
            'heure_derniere_pause': False
        })
        
        self.message_post(
            body=_("Traitement repris après pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_terminer_traitement(self):
        """Termine le traitement"""
        self.ensure_one()
        
        if self.state not in ['en_cours', 'pause']:
            raise UserError(_("Seuls les traitements en cours ou en pause peuvent être terminés."))
        
        if not self.radical_dossier or not self.code_agence:
            raise UserError(_("Veuillez remplir le radical dossier et le code agence avant de terminer."))
        
        # Si en pause, calculer la durée de la dernière pause
        if self.state == 'pause' and self.heure_derniere_pause:
            duree_pause = (fields.Datetime.now() - self.heure_derniere_pause).total_seconds() / 60
            self.duree_pauses += duree_pause
        
        self.write({
            'heure_fin': fields.Datetime.now(),
            'state': 'termine',
            'heure_derniere_pause': False
        })
        
        self.message_post(
            body=_("Traitement terminé en %d minutes (durée effective: %d min)") % (
                self.duree_traitement, self.duree_effective),
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Traitement Terminé'),
                'message': _('Durée: %d minutes | Vitesse: %.2f pièces/min') % (
                    self.duree_traitement, self.vitesse_traitement),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_valider_traitement(self):
        """Valide le traitement et passe à l'étape suivante"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Seuls les traitements terminés peuvent être validés."))
        
        self.state = 'valide'
        
        # Valider le traitement au niveau du dossier collecteur
        self.dossier_id.action_valider_traitement()
        
        self.message_post(
            body=_("Traitement validé et transféré vers l'étape suivante"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_reprendre_traitement_termine(self):
        """Reprend un traitement terminé pour modification"""
        self.ensure_one()
        
        if self.state not in ['termine', 'valide']:
            raise UserError(_("Seuls les traitements terminés peuvent être repris."))
        
        self.write({
            'heure_fin': False,
            'state': 'en_cours'
        })
        
        self.message_post(
            body=_("Traitement repris pour modification"),
            subtype_xmlid='mail.mt_note'
        )
    
    # === ACTIONS D'INTERFACE ===
    def action_voir_dossier(self):
        """Ouvre le dossier collecteur associé"""
        self.ensure_one()
        
        return {
            'name': _('Dossier Collecteur'),
            'type': 'ir.actions.act_window',
            'res_model': 'dossier.collecteur',
            'res_id': self.dossier_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_historique_traitements(self):
        """Affiche l'historique des traitements de l'agent"""
        self.ensure_one()
        
        return {
            'name': _('Historique des Traitements - %s') % self.agent_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'traitement.physique',
            'view_mode': 'tree,form',
            'domain': [('agent_id', '=', self.agent_id.id)],
            'context': {'search_default_agent_id': self.agent_id.id},
            'target': 'current',
        }
    
    # === CONTRAINTES ===
    @api.constrains('radical_dossier')
    def _check_radical_dossier(self):
        for record in self:
            if record.radical_dossier and len(record.radical_dossier) < 2:
                raise ValidationError(_("Le radical dossier doit contenir au moins 2 caractères."))
    
    @api.constrains('code_agence')
    def _check_code_agence(self):
        for record in self:
            if record.code_agence and not record.code_agence.replace('-', '').replace('_', '').isalnum():
                raise ValidationError(_("Le code agence doit être alphanumérique."))
    
    @api.constrains('nombre_pieces_traitees')
    def _check_nombre_pieces(self):
        for record in self:
            if record.nombre_pieces_traitees < 0:
                raise ValidationError(_("Le nombre de pièces traitées ne peut pas être négatif."))
    
    @api.constrains('duree_pauses')
    def _check_duree_pauses(self):
        for record in self:
            if record.duree_pauses < 0:
                raise ValidationError(_("La durée des pauses ne peut pas être négative."))
            if record.duree_traitement > 0 and record.duree_pauses > record.duree_traitement:
                raise ValidationError(_("La durée des pauses ne peut pas être supérieure à la durée totale."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            if record.radical_dossier:
                name = f"{record.dossier_id.numero_dossier} - {record.radical_dossier}"
            else:
                name = record.dossier_id.numero_dossier or _('Nouveau')
            
            if record.state:
                state_name = dict(record._fields['state'].selection)[record.state]
                name += f" ({state_name})"
            
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', '|', ('radical_dossier', operator, name), 
                   ('code_agence', operator, name),
                   ('dossier_id.numero_dossier', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
    
    # === MÉTHODES DE REPORTING ===
    @api.model
    def get_kpi_agent(self, agent_id, date_debut=None, date_fin=None):
        """Retourne les KPIs d'un agent pour une période donnée"""
        domain = [('agent_id', '=', agent_id), ('state', '=', 'valide')]
        
        if date_debut:
            domain.append(('heure_debut', '>=', date_debut))
        if date_fin:
            domain.append(('heure_fin', '<=', date_fin))
        
        traitements = self.search(domain)
        
        if not traitements:
            return {
                'nombre_dossiers': 0,
                'duree_moyenne': 0,
                'duree_totale': 0,
                'vitesse_moyenne': 0,
                'nombre_pieces_total': 0
            }
        
        return {
            'nombre_dossiers': len(traitements),
            'duree_moyenne': sum(traitements.mapped('duree_effective')) / len(traitements),
            'duree_totale': sum(traitements.mapped('duree_effective')),
            'vitesse_moyenne': sum(traitements.mapped('vitesse_traitement')) / len(traitements),
            'nombre_pieces_total': sum(traitements.mapped('nombre_pieces_traitees'))
        }

