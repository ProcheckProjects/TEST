# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class ReceptionDossier(models.Model):
    _name = 'reception.dossier'
    _description = 'Réception des Dossiers Collecteurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reception desc'
    _rec_name = 'numero_reception'

    # === INFORMATIONS DE RÉCEPTION ===
    numero_reception = fields.Char(
        string='N° Réception', 
        required=True,
        copy=False,
        readonly=True,
        states={'brouillon': [('readonly', False)]},
        tracking=True,
        help="Numéro de réception généré automatiquement"
    )
    
    date_reception = fields.Datetime(
        string='Date de Réception', 
        default=fields.Datetime.now,
        required=True,
        tracking=True,
        help="Date et heure de réception des dossiers"
    )
    
    heure_arrivee = fields.Datetime(
        string='Heure d\'arrivée', 
        tracking=True,
        help="Heure d'arrivée du coursier"
    )
    
    heure_reception = fields.Datetime(
        string='Heure de Réception', 
        tracking=True,
        help="Heure effective de réception des dossiers"
    )
    
    coursier = fields.Char(
        string='Coursier', 
        tracking=True,
        help="Nom du coursier qui a livré les dossiers"
    )
    
    bordereau_livraison = fields.Char(
        string='N° Bordereau de Livraison', 
        required=True, 
        tracking=True,
        help="Numéro du bordereau de livraison du bureau d'ordre"
    )
    
    # === DÉTAILS DES DOSSIERS ===
    type_dossier = fields.Selection([
        ('collecteur', 'Dossier Collecteur')
    ], string='Type de Dossier', required=True, default='collecteur', tracking=True)
    
    nombre_dossiers = fields.Integer(
        string='Nombre de Dossiers Reçus', 
        required=True,
        tracking=True,
        help="Nombre total de dossiers reçus dans cette réception"
    )
    
    # === RELATIONS ===
    dossier_ids = fields.One2many(
        'dossier.collecteur', 
        'reception_id', 
        string='Dossiers Collecteurs',
        help="Liste des dossiers collecteurs créés pour cette réception"
    )
    
    archiviste_id = fields.Many2one(
        'res.users', 
        string='Archiviste', 
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=[('groups_id', 'in', [lambda self: self.env.ref('archivage_secondv.group_archiviste').id])],
        help="Archiviste responsable de la réception"
    )
    
    # === ÉTATS ET VALIDATION ===
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('valide', 'Validé'),
        ('en_cours', 'En Cours de Traitement'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé')
    ], string='État', default='brouillon', tracking=True, help="État de la réception")
    
    # === CHAMPS CALCULÉS ===
    nombre_dossiers_crees = fields.Integer(
        string='Dossiers Créés',
        compute='_compute_nombre_dossiers_crees',
        store=True,
        help="Nombre de dossiers collecteurs effectivement créés"
    )
    
    nombre_dossiers_traites = fields.Integer(
        string='Dossiers Traités', 
        compute='_compute_nombre_dossiers_traites', 
        store=True,
        help="Nombre de dossiers déjà traités"
    )
    
    progression = fields.Float(
        string='Progression (%)',
        compute='_compute_progression',
        help="Pourcentage de progression du traitement"
    )
    
    duree_traitement_totale = fields.Float(
        string='Durée Totale (heures)',
        compute='_compute_duree_traitement_totale',
        help="Durée totale de traitement de tous les dossiers"
    )
    
    duree_moyenne_par_dossier = fields.Float(
        string='Durée Moyenne par Dossier (heures)', 
        compute='_compute_duree_moyenne_par_dossier', 
        store=True,
        help="Durée moyenne de traitement par dossier"
    )
    
    # === CONTRÔLES QUALITÉ ===
    controle_nombre = fields.Boolean(
        string='Contrôle Nombre de Dossiers', 
        default=False,
        help="Contrôle de conformité du nombre de dossiers"
    )
    
    controle_etat = fields.Boolean(
        string='Contrôle État des Dossiers', 
        default=False,
        help="Contrôle de l'état physique des dossiers"
    )
    
    controle_completude = fields.Boolean(
        string='Contrôle Complétude des Dossiers', 
        default=False,
        help="Contrôle de la complétude des dossiers"
    )
    
    controle_bordereau = fields.Boolean(
        string='Contrôle Bordereau de Livraison', 
        default=False,
        help="Contrôle du bordereau de livraison"
    )
    
    controle_signature = fields.Boolean(
        string='Contrôle Signature Bordereau', 
        default=False,
        help="Contrôle de la signature du bordereau"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes et observations sur la réception"
    )
    
    observation_conformite = fields.Text(
        string='Observations Conformité',
        help="Observations sur la conformité des dossiers reçus"
    )
    
    anomalies_detectees = fields.Text(
        string='Anomalies Détectées',
        help="Anomalies détectées lors de la réception"
    )
    
    observations = fields.Text(
        string='Observations Particulières',
        help="Observations particulières sur la réception"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('dossier_ids')
    def _compute_nombre_dossiers_crees(self):
        for record in self:
            record.nombre_dossiers_crees = len(record.dossier_ids)
    
    @api.depends('dossier_ids.state')
    def _compute_nombre_dossiers_traites(self):
        for record in self:
            record.nombre_dossiers_traites = len(record.dossier_ids.filtered(lambda d: d.state != 'reception'))
    
    @api.depends('dossier_ids.state')
    def _compute_progression(self):
        for record in self:
            if not record.dossier_ids:
                record.progression = 0
            else:
                total_dossiers = len(record.dossier_ids)
                dossiers_termines = len(record.dossier_ids.filtered(lambda d: d.state == 'livre'))
                record.progression = (dossiers_termines / total_dossiers) * 100 if total_dossiers > 0 else 0
    
    @api.depends('dossier_ids.duree_totale')
    def _compute_duree_traitement_totale(self):
        for record in self:
            record.duree_traitement_totale = sum(record.dossier_ids.mapped('duree_totale'))
    
    @api.depends('dossier_ids.duree_totale', 'nombre_dossiers_traites')
    def _compute_duree_moyenne_par_dossier(self):
        for record in self:
            if record.nombre_dossiers_traites > 0:
                record.duree_moyenne_par_dossier = sum(record.dossier_ids.mapped('duree_totale')) / record.nombre_dossiers_traites
            else:
                record.duree_moyenne_par_dossier = 0.0
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        if not vals.get('numero_reception'):
            vals['numero_reception'] = self.env['ir.sequence'].next_by_code('reception.dossier') or _('New')
        return super(ReceptionDossier, self).create(vals)
    
    # === ACTIONS PRINCIPALES ===
    def action_valider_reception(self):
        """Valide la réception et crée les dossiers collecteurs"""
        self.ensure_one()
        
        if self.state != 'brouillon':
            raise UserError(_("Seules les réceptions en brouillon peuvent être validées."))
        
        if self.nombre_dossiers <= 0:
            raise UserError(_("Le nombre de dossiers doit être supérieur à 0."))
        
        # Créer les dossiers collecteurs
        self._create_dossiers_collecteurs()
        
        self.state = 'valide'
        self.message_post(
            body=_("Réception validée - %d dossiers collecteurs créés") % self.nombre_dossiers,
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Réception Validée'),
                'message': _('%d dossiers collecteurs créés avec succès') % self.nombre_dossiers,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_demarrer_traitement(self):
        """Démarre le traitement des dossiers"""
        self.ensure_one()
        
        if self.state != 'valide':
            raise UserError(_("Seules les réceptions validées peuvent être démarrées."))
        
        # Passer tous les dossiers en état traitement
        for dossier in self.dossier_ids:
            if dossier.state == 'reception':
                dossier.action_demarrer_traitement()
        
        self.state = 'en_cours'
        self.message_post(
            body=_("Traitement démarré pour tous les dossiers"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_terminer_reception(self):
        """Termine la réception"""
        self.ensure_one()
        if self.state != 'en_cours':
            raise UserError(_("Seules les réceptions en cours peuvent être terminées."))
        
        dossiers_non_termines = self.dossier_ids.filtered(lambda d: d.state != 'livre')
        if dossiers_non_termines:
            raise UserError(_("Impossible de terminer la réception : tous les dossiers ne sont pas encore livrés."))

        self.state = 'termine'
        self.message_post(
            body=_("Réception terminée avec succès."),
            subtype_xmlid='mail.mt_comment'
        )

    def action_annuler_reception(self):
        """Annule la réception"""
        self.ensure_one()
        if self.state in ['termine']:
            raise UserError(_("Impossible d'annuler une réception terminée."))
        
        self.state = 'annule'
        self.message_post(
            body=_("Réception annulée."),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_retour_brouillon(self):
        """Remet la réception en brouillon"""
        self.ensure_one()
        
        if self.state == 'termine':
            raise UserError(_("Impossible de remettre en brouillon une réception terminée."))
        
        if self.dossier_ids.filtered(lambda d: d.state not in ['reception']):
            raise UserError(_("Impossible de remettre en brouillon : certains dossiers sont déjà en cours de traitement."))
        
        self.state = 'brouillon'
        self.message_post(
            body=_("Réception remise en brouillon"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_voir_dossiers(self):
        """Ouvre la vue des dossiers collecteurs de cette réception"""
        self.ensure_one()
        
        return {
            'name': _('Dossiers Collecteurs - %s') % self.numero_reception,
            'type': 'ir.actions.act_window',
            'res_model': 'dossier.collecteur',
            'view_mode': 'tree,form,kanban',
            'domain': [('reception_id', '=', self.id)],
            'context': {
                'default_reception_id': self.id,
                'search_default_reception_id': self.id,
            },
            'target': 'current',
        }
    
    def action_voir_traitements(self):
        """Ouvre la vue des traitements des dossiers de cette réception"""
        self.ensure_one()
        return {
            'name': _('Traitements des Dossiers - %s') % self.numero_reception,
            'type': 'ir.actions.act_window',
            'res_model': 'dossier.collecteur',
            'view_mode': 'tree,form,kanban',
            'domain': [('reception_id', '=', self.id)],
            'context': {
                'default_reception_id': self.id,
                'search_default_reception_id': self.id,
            },
            'target': 'current',
        }
    
    # === MÉTHODES PRIVÉES ===
    def _create_dossiers_collecteurs(self):
        """Crée les dossiers collecteurs selon le nombre spécifié"""
        self.ensure_one()
        
        # Supprimer les dossiers existants si nécessaire
        self.dossier_ids.unlink()
        
        # Créer les nouveaux dossiers
        dossiers_vals = []
        for i in range(1, self.nombre_dossiers + 1):
            dossiers_vals.append({
                'reception_id': self.id,
                'type_dossier': self.type_dossier,
                'state': 'reception',
                'date_reception': self.date_reception,
                'archiviste_id': self.archiviste_id.id,
            })
        
        self.env['dossier.collecteur'].create(dossiers_vals)
    
    def _check_completion(self):
        """Vérifie si tous les dossiers sont terminés"""
        self.ensure_one()
        
        if self.state == 'en_cours':
            dossiers_non_termines = self.dossier_ids.filtered(lambda d: d.state != 'livre')
            if not dossiers_non_termines:
                self.state = 'termine'
                self.message_post(
                    body=_("Tous les dossiers ont été traités et livrés"),
                    subtype_xmlid='mail.mt_comment'
                )
    
    # === CONTRAINTES ===
    @api.constrains('nombre_dossiers')
    def _check_nombre_dossiers(self):
        for record in self:
            if record.nombre_dossiers <= 0:
                raise ValidationError(_("Le nombre de dossiers doit être supérieur à 0."))
            if record.nombre_dossiers > 1000:
                raise ValidationError(_("Le nombre de dossiers ne peut pas dépasser 1000 par réception."))
    
    @api.constrains('date_reception')
    def _check_date_reception(self):
        for record in self:
            if record.date_reception > fields.Datetime.now():
                raise ValidationError(_("La date de réception ne peut pas être dans le futur."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.numero_reception}"
            if record.nombre_dossiers:
                name += f" ({record.nombre_dossiers} dossiers)"
            if record.state:
                state_name = dict(record._fields['state'].selection)[record.state]
                name += f" - {state_name}"
            result.append((record.id, name))
        return result
    
    # === MÉTHODES DE RECHERCHE ===
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', ('numero_reception', operator, name), ('bordereau_livraison', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

