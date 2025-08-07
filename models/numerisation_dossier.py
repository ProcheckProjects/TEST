# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class NumerisationDossier(models.Model):
    _name = 'numerisation.dossier'
    _description = 'Numérisation des Dossiers Collecteurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'heure_debut desc'
    _rec_name = 'display_name'

    # === IDENTIFICATION ===
    dossier_id = fields.Many2one(
        'dossier.collecteur', 
        string='Dossier Collecteur', 
        required=True,
        ondelete='cascade',
        help="Dossier collecteur à numériser"
    )

    operateur_id = fields.Many2one(
        'res.users',
        string='Opérateur de Numérisation',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=lambda self: [
            ("groups_id", "in", [self.env.ref("archivage_secondv.group_operateur_numerisation").id])
        ],
        help="Opérateur responsable de la numérisation"
    )
    
    # === GESTION DU TEMPS ===
    heure_debut = fields.Datetime(
        string='Heure de Début', 
        default=fields.Datetime.now,
        readonly=True,
        help="Heure de début de la numérisation (automatique)"
    )
    
    heure_fin = fields.Datetime(
        string='Heure de Fin', 
        readonly=True,
        help="Heure de fin de la numérisation (automatique)"
    )
    
    duree_numerisation = fields.Float(
        string='Durée (minutes)', 
        compute='_compute_duree_numerisation',
        store=True,
        readonly=True,
        help="Durée de la numérisation en minutes (calculée automatiquement)"
    )
    
    # === MÉTRIQUES DE NUMÉRISATION ===
    nombre_dossiers = fields.Integer(
        string='Nombre de Dossiers', 
        default=1,
        readonly=True,
        help="Nombre de dossiers numérisés (automatique)"
    )
    
    nombre_pieces = fields.Integer(
        string='Nombre de Pièces',
        required=True,
        help="Nombre total de pièces numérisées"
    )
    
    nombre_pages = fields.Integer(
        string='Nombre de Pages',
        help="Nombre total de pages numérisées"
    )
    
    # === QUALITÉ ET PARAMÈTRES ===
    qualite_numerisation = fields.Selection([
        ('300dpi', '300 DPI'),
        ('600dpi', '600 DPI'),
        ('1200dpi', '1200 DPI')
    ], string='Qualité', default='300dpi', help="Qualité de numérisation")
    
    format_fichier = fields.Selection([
        ('pdf', 'PDF'),
        ('tiff', 'TIFF'),
        ('jpeg', 'JPEG')
    ], string='Format', default='pdf', help="Format des fichiers numérisés")
    
    couleur = fields.Selection([
        ('couleur', 'Couleur'),
        ('niveaux_gris', 'Niveaux de Gris'),
        ('noir_blanc', 'Noir et Blanc')
    ], string='Mode Couleur', default='couleur', help="Mode de couleur")
    
    # === ÉTAT DE LA NUMÉRISATION ===
    state = fields.Selection([
        ('en_cours', 'En Cours'),
        ('pause', 'En Pause'),
        ('termine', 'Terminé'),
        ('valide', 'Validé'),
        ('erreur', 'Erreur')
    ], string='État', default='en_cours', tracking=True, help="État actuel de la numérisation")
    
    # === GESTION DES PAUSES ===
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
    
    # === INFORMATIONS TECHNIQUES ===
    scanner_utilise = fields.Char(
        string='Scanner Utilisé',
        help="Identifiant du scanner utilisé"
    )
    
    taille_fichiers = fields.Float(
        string='Taille Fichiers (MB)',
        help="Taille totale des fichiers numérisés en MB"
    )
    
    # === CONTRÔLE QUALITÉ ===
    controle_qualite = fields.Boolean(
        string='Contrôle Qualité Effectué',
        default=False,
        help="Indique si le contrôle qualité a été effectué"
    )
    
    problemes_qualite = fields.Text(
        string='Problèmes de Qualité',
        help="Description des problèmes de qualité rencontrés"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes sur la numérisation"
    )
    
    observations = fields.Text(
        string='Observations',
        help="Observations particulières"
    )
    
    # === CHAMP D'AFFICHAGE ===
    display_name = fields.Char(
        string='Nom',
        compute='_compute_display_name',
        store=True,
        help="Nom d'affichage de la numérisation"
    )
    
    # === MÉTRIQUES DE PERFORMANCE ===
    vitesse_numerisation = fields.Float(
        string='Vitesse (pièces/min)',
        compute='_compute_vitesse_numerisation',
        help="Vitesse de numérisation en pièces par minute"
    )
    
    duree_effective = fields.Float(
        string='Durée Effective (min)',
        compute='_compute_duree_effective',
        help="Durée effective sans les pauses"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('heure_debut', 'heure_fin')
    def _compute_duree_numerisation(self):
        for record in self:
            if record.heure_debut and record.heure_fin:
                delta = record.heure_fin - record.heure_debut
                record.duree_numerisation = delta.total_seconds() / 60
            else:
                record.duree_numerisation = 0
    
    @api.depends('duree_numerisation', 'duree_pauses')
    def _compute_duree_effective(self):
        for record in self:
            record.duree_effective = record.duree_numerisation - record.duree_pauses
    
    @api.depends('nombre_pieces', 'duree_effective')
    def _compute_vitesse_numerisation(self):
        for record in self:
            if record.duree_effective > 0 and record.nombre_pieces > 0:
                record.vitesse_numerisation = record.nombre_pieces / record.duree_effective
            else:
                record.vitesse_numerisation = 0
    
    @api.depends('dossier_id')
    def _compute_display_name(self):
        for record in self:
            if record.dossier_id and record.numero_carton:
                record.display_name = f"{record.dossier_id.numero_dossier} - Carton {record.numero_carton}"
            elif record.dossier_id:
                record.display_name = record.dossier_id.numero_dossier
            else:
                record.display_name = _('Nouvelle numérisation')
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        """Démarre automatiquement le chronomètre à la création"""
        if 'heure_debut' not in vals:
            vals['heure_debut'] = fields.Datetime.now()
        
        numerisation = super(NumerisationDossier, self).create(vals)
        
        # Lier la numérisation au dossier
        if numerisation.dossier_id:
            numerisation.dossier_id.numerisation_id = numerisation.id
            numerisation.dossier_id.date_debut_numerisation = numerisation.heure_debut
        
        return numerisation
    
    def write(self, vals):
        """Met à jour les informations du dossier lors de la modification"""
        result = super(NumerisationDossier, self).write(vals)
        
        # Mettre à jour le dossier collecteur si nécessaire
        for record in self:
            if any(field in vals for field in ['type_dossier_detail', 'numero_carton']):
                record.dossier_id.write({
                    'type_dossier_detail': record.type_dossier_detail,
                    'numero_carton': record.numero_carton,
                    'operateur_numerisation_id': record.operateur_id.id,
                    'observations_numerisation': record.observations,
                })
        
        return result
    
    # === ACTIONS PRINCIPALES ===
    def action_mettre_en_pause(self):
        """Met la numérisation en pause"""
        self.ensure_one()
        
        if self.state != 'en_cours':
            raise UserError(_("Seules les numérisations en cours peuvent être mises en pause."))
        
        self.write({
            'state': 'pause',
            'heure_derniere_pause': fields.Datetime.now(),
            'nombre_pauses': self.nombre_pauses + 1
        })
        
        self.message_post(
            body=_("Numérisation mise en pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_reprendre_numerisation(self):
        """Reprend la numérisation après une pause"""
        self.ensure_one()
        
        if self.state != 'pause':
            raise UserError(_("Seules les numérisations en pause peuvent être reprises."))
        
        if self.heure_derniere_pause:
            duree_pause = (fields.Datetime.now() - self.heure_derniere_pause).total_seconds() / 60
            self.duree_pauses += duree_pause
        
        self.write({
            'state': 'en_cours',
            'heure_derniere_pause': False
        })
        
        self.message_post(
            body=_("Numérisation reprise après pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_terminer_numerisation(self):
        """Termine la numérisation"""
        self.ensure_one()
        
        if self.state not in ['en_cours', 'pause']:
            raise UserError(_("Seules les numérisations en cours ou en pause peuvent être terminées."))
        
        if not self.numero_carton or not self.type_dossier_detail:
            raise UserError(_("Veuillez remplir le numéro de carton et le type de dossier."))
        
        if self.nombre_pieces <= 0:
            raise UserError(_("Le nombre de pièces doit être supérieur à 0."))
        
        # Si en pause, calculer la durée de la dernière pause
        if self.state == 'pause' and self.heure_derniere_pause:
            duree_pause = (fields.Datetime.now() - self.heure_derniere_pause).total_seconds() / 60
            self.duree_pauses += duree_pause
        
        self.write({
            'heure_fin': fields.Datetime.now(),
            'state': 'termine',
            'heure_derniere_pause': False
        })
        
        # Mettre à jour le dossier collecteur
        self.dossier_id.date_fin_numerisation = self.heure_fin
        
        self.message_post(
            body=_("Numérisation terminée - %d pièces en %d minutes (vitesse: %.2f pièces/min)") % (
                self.nombre_pieces, self.duree_numerisation, self.vitesse_numerisation),
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Numérisation Terminée'),
                'message': _('%d pièces numérisées en %d minutes') % (
                    self.nombre_pieces, self.duree_numerisation),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_valider_numerisation(self):
        """Valide la numérisation et passe à l'étape suivante"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Seules les numérisations terminées peuvent être validées."))
        
        if not self.controle_qualite:
            raise UserError(_("Le contrôle qualité doit être effectué avant la validation."))
        
        self.state = 'valide'
        
        # Valider la numérisation au niveau du dossier collecteur
        self.dossier_id.action_valider_numerisation()
        
        self.message_post(
            body=_("Numérisation validée et transférée vers l'indexation"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_effectuer_controle_qualite(self):
        """Effectue le contrôle qualité"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Le contrôle qualité ne peut être effectué que sur les numérisations terminées."))
        
        self.controle_qualite = True
        self.message_post(
            body=_("Contrôle qualité effectué"),
            subtype_xmlid='mail.mt_note'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contrôle Qualité'),
                'message': _('Contrôle qualité effectué avec succès'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_signaler_erreur(self):
        """Signale une erreur dans la numérisation"""
        self.ensure_one()
        
        self.state = 'erreur'
        self.message_post(
            body=_("Erreur signalée dans la numérisation"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_reprendre_numerisation_terminee(self):
        """Reprend une numérisation terminée pour modification"""
        self.ensure_one()
        
        if self.state not in ['termine', 'valide', 'erreur']:
            raise UserError(_("Seules les numérisations terminées peuvent être reprises."))
        
        self.write({
            'heure_fin': False,
            'state': 'en_cours',
            'controle_qualite': False
        })
        
        self.message_post(
            body=_("Numérisation reprise pour modification"),
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
    
    def action_voir_carton(self):
        """Ouvre le carton associé"""
        self.ensure_one()
        
        if not self.carton_id:
            raise UserError(_("Aucun carton associé à cette numérisation."))
        
        return {
            'name': _('Carton de Numérisation'),
            'type': 'ir.actions.act_window',
            'res_model': 'carton.numerisation',
            'res_id': self.carton_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_historique_numerisations(self):
        """Affiche l'historique des numérisations de l'opérateur"""
        self.ensure_one()
        
        return {
            'name': _('Historique des Numérisations - %s') % self.operateur_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'numerisation.dossier',
            'view_mode': 'tree,form',
            'domain': [('operateur_id', '=', self.operateur_id.id)],
            'context': {'search_default_operateur_id': self.operateur_id.id},
            'target': 'current',
        }
    
    # === CONTRAINTES ===
    @api.constrains('nombre_pieces')
    def _check_nombre_pieces(self):
        for record in self:
            if record.state == 'termine' and record.nombre_pieces <= 0:
                raise ValidationError(_("Le nombre de pièces doit être supérieur à 0."))
    
    @api.constrains('numero_carton')
    def _check_numero_carton(self):
        for record in self:
            if not record.numero_carton or len(record.numero_carton) < 1:
                raise ValidationError(_("Le numéro de carton est obligatoire."))
    
    @api.constrains('duree_pauses')
    def _check_duree_pauses(self):
        for record in self:
            if record.duree_pauses < 0:
                raise ValidationError(_("La durée des pauses ne peut pas être négative."))
            if record.duree_numerisation > 0 and record.duree_pauses > record.duree_numerisation:
                raise ValidationError(_("La durée des pauses ne peut pas être supérieure à la durée totale."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            if record.numero_carton:
                name = f"{record.dossier_id.numero_dossier} - Carton {record.numero_carton}"
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
            args = ['|', '|', ('numero_carton', operator, name), 
                   ('dossier_id.numero_dossier', operator, name),
                   ('dossier_id.radical_dossier', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
    
    # === MÉTHODES DE REPORTING ===
    @api.model
    def get_kpi_operateur(self, operateur_id, date_debut=None, date_fin=None):
        """Retourne les KPIs d'un opérateur pour une période donnée"""
        domain = [('operateur_id', '=', operateur_id), ('state', '=', 'valide')]
        
        if date_debut:
            domain.append(('heure_debut', '>=', date_debut))
        if date_fin:
            domain.append(('heure_fin', '<=', date_fin))
        
        numerisations = self.search(domain)
        
        if not numerisations:
            return {
                'nombre_dossiers': 0,
                'duree_moyenne': 0,
                'duree_totale': 0,
                'vitesse_moyenne': 0,
                'nombre_pieces_total': 0
            }
        
        return {
            'nombre_dossiers': len(numerisations),
            'duree_moyenne': sum(numerisations.mapped('duree_effective')) / len(numerisations),
            'duree_totale': sum(numerisations.mapped('duree_effective')),
            'vitesse_moyenne': sum(numerisations.mapped('vitesse_numerisation')) / len(numerisations),
            'nombre_pieces_total': sum(numerisations.mapped('nombre_pieces'))
        }

