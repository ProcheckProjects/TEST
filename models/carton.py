# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class CartonNumerisation(models.Model):
    _name = 'carton.numerisation'
    _description = 'Carton de Numérisation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'numero_carton desc'
    _rec_name = 'numero_carton'

    # === IDENTIFICATION ===
    numero_carton = fields.Char(
        string='N° Carton', 
        required=True,
        copy=False,
        tracking=True,
        help="Numéro unique du carton (généré automatiquement ou saisi manuellement)"
    )
    
    date_creation = fields.Datetime(
        string='Date de Création', 
        default=fields.Datetime.now,
        readonly=True,
        help="Date de création du carton"
    )
    
    # === INFORMATIONS DU CARTON ===
    type_dossier = fields.Selection([
        ('pret', 'Prêt'),
        ('equipement', 'Équipement'),
        ('compte', 'Compte'),
        ('evenement', 'Événement')
    ], string='Type de Dossier', required=True, tracking=True, 
       help="Type de dossiers contenus dans le carton")
    
    capacite_max = fields.Integer(
        string='Capacité Maximum',
        default=50,
        help="Nombre maximum de dossiers que peut contenir le carton"
    )
    
    # === RELATIONS ===
    dossier_ids = fields.One2many(
        'dossier.collecteur', 
        'carton_id', 
        string='Dossiers',
        help="Dossiers collecteurs contenus dans ce carton"
    )
    
    operateur_id = fields.Many2one(
        'res.users', 
        string='Opérateur', 
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=[('groups_id', 'in', [lambda self: self.env.ref('archivage_collecteurs_complet.group_operateur_numerisation').id])],
        help="Opérateur responsable du carton"
    )
    
    # === ÉTAT ET PROGRESSION ===
    state = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('en_cours', 'En Cours de Remplissage'),
        ('plein', 'Plein'),
        ('termine', 'Terminé'),
        ('numerise', 'Numérisé')
    ], string='État', default='ouvert', tracking=True, help="État actuel du carton")
    
    # === CHAMPS CALCULÉS ===
    nombre_dossiers = fields.Integer(
        string='Nombre de Dossiers',
        compute='_compute_nombre_dossiers',
        store=True,
        help="Nombre de dossiers actuellement dans le carton"
    )
    
    taux_remplissage = fields.Float(
        string='Taux de Remplissage (%)',
        compute='_compute_taux_remplissage',
        help="Pourcentage de remplissage du carton"
    )
    
    espace_disponible = fields.Integer(
        string='Espace Disponible',
        compute='_compute_espace_disponible',
        help="Nombre de dossiers pouvant encore être ajoutés"
    )
    
    # === MÉTRIQUES DE NUMÉRISATION ===
    date_debut_numerisation = fields.Datetime(
        string='Début Numérisation',
        help="Date de début de la numérisation du carton"
    )
    
    date_fin_numerisation = fields.Datetime(
        string='Fin Numérisation',
        help="Date de fin de la numérisation du carton"
    )
    
    duree_numerisation = fields.Float(
        string='Durée Numérisation (min)',
        compute='_compute_duree_numerisation',
        store=True,
        help="Durée totale de numérisation en minutes"
    )
    
    nombre_pieces_total = fields.Integer(
        string='Nombre Total de Pièces',
        compute='_compute_nombre_pieces_total',
        store=True,
        help="Nombre total de pièces numérisées dans le carton"
    )
    
    # === INFORMATIONS COMPLÉMENTAIRES ===
    emplacement_physique = fields.Char(
        string='Emplacement Physique',
        help="Emplacement physique du carton dans l'entrepôt"
    )
    
    priorite = fields.Selection([
        ('normale', 'Normale'),
        ('urgente', 'Urgente'),
        ('critique', 'Critique')
    ], string='Priorité', default='normale', tracking=True)
    
    # === NOTES ===
    notes = fields.Text(
        string='Notes',
        help="Notes sur le carton"
    )
    
    observations = fields.Text(
        string='Observations',
        help="Observations particulières"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('dossier_ids')
    def _compute_nombre_dossiers(self):
        for record in self:
            record.nombre_dossiers = len(record.dossier_ids)
    
    @api.depends('nombre_dossiers', 'capacite_max')
    def _compute_taux_remplissage(self):
        for record in self:
            if record.capacite_max > 0:
                record.taux_remplissage = (record.nombre_dossiers / record.capacite_max) * 100
            else:
                record.taux_remplissage = 0
    
    @api.depends('nombre_dossiers', 'capacite_max')
    def _compute_espace_disponible(self):
        for record in self:
            record.espace_disponible = max(0, record.capacite_max - record.nombre_dossiers)
    
    @api.depends('date_debut_numerisation', 'date_fin_numerisation')
    def _compute_duree_numerisation(self):
        for record in self:
            if record.date_debut_numerisation and record.date_fin_numerisation:
                delta = record.date_fin_numerisation - record.date_debut_numerisation
                record.duree_numerisation = delta.total_seconds() / 60
            else:
                record.duree_numerisation = 0
    
    @api.depends('dossier_ids.nombre_pieces')
    def _compute_nombre_pieces_total(self):
        for record in self:
            record.nombre_pieces_total = sum(record.dossier_ids.mapped('nombre_pieces'))
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        if not vals.get('numero_carton'):
            vals['numero_carton'] = self._generate_numero_carton()
        return super(CartonNumerisation, self).create(vals)
    
    def _generate_numero_carton(self):
        """Génère automatiquement un numéro de carton"""
        sequence = self.env['ir.sequence'].next_by_code('carton.numerisation')
        if not sequence:
            # Fallback si la séquence n'existe pas
            last_carton = self.search([], order='id desc', limit=1)
            if last_carton and last_carton.numero_carton.isdigit():
                next_num = int(last_carton.numero_carton) + 1
            else:
                next_num = 1
            sequence = str(next_num).zfill(6)
        return sequence
    
    # === ACTIONS PRINCIPALES ===
    def action_incrementer_numero(self):
        """Incrémente manuellement le numéro de carton"""
        self.ensure_one()
        
        if self.state != 'ouvert':
            raise UserError(_("Seuls les cartons ouverts peuvent avoir leur numéro incrémenté."))
        
        if self.dossier_ids:
            raise UserError(_("Impossible d'incrémenter le numéro d'un carton contenant déjà des dossiers."))
        
        # Extraire le numéro et l'incrémenter
        try:
            if self.numero_carton.isdigit():
                nouveau_numero = str(int(self.numero_carton) + 1).zfill(len(self.numero_carton))
            else:
                # Si le numéro contient des lettres, essayer d'extraire la partie numérique
                import re
                match = re.search(r'(\d+)', self.numero_carton)
                if match:
                    num_part = match.group(1)
                    new_num = str(int(num_part) + 1).zfill(len(num_part))
                    nouveau_numero = self.numero_carton.replace(num_part, new_num)
                else:
                    raise UserError(_("Impossible d'incrémenter ce format de numéro."))
            
            self.numero_carton = nouveau_numero
            self.message_post(
                body=_("Numéro de carton incrémenté à : %s") % nouveau_numero,
                subtype_xmlid='mail.mt_note'
            )
            
        except Exception as e:
            raise UserError(_("Erreur lors de l'incrémentation : %s") % str(e))
    
    def action_ajouter_dossier(self, dossier_id):
        """Ajoute un dossier au carton"""
        self.ensure_one()
        
        if self.state not in ['ouvert', 'en_cours']:
            raise UserError(_("Impossible d'ajouter des dossiers à un carton fermé."))
        
        if self.espace_disponible <= 0:
            raise UserError(_("Le carton est plein. Capacité maximum atteinte."))
        
        dossier = self.env['dossier.collecteur'].browse(dossier_id)
        if not dossier.exists():
            raise UserError(_("Dossier introuvable."))
        
        if dossier.carton_id:
            raise UserError(_("Ce dossier est déjà assigné à un carton."))
        
        # Assigner le dossier au carton
        dossier.carton_id = self.id
        dossier.numero_carton = self.numero_carton
        
        # Mettre à jour l'état du carton
        if self.state == 'ouvert':
            self.state = 'en_cours'
        
        if self.espace_disponible <= 0:
            self.state = 'plein'
        
        self.message_post(
            body=_("Dossier %s ajouté au carton") % dossier.numero_dossier,
            subtype_xmlid='mail.mt_note'
        )
    
    def action_retirer_dossier(self, dossier_id):
        """Retire un dossier du carton"""
        self.ensure_one()
        
        if self.state == 'numerise':
            raise UserError(_("Impossible de retirer des dossiers d'un carton déjà numérisé."))
        
        dossier = self.env['dossier.collecteur'].browse(dossier_id)
        if not dossier.exists() or dossier.carton_id.id != self.id:
            raise UserError(_("Ce dossier n'appartient pas à ce carton."))
        
        # Retirer le dossier du carton
        dossier.carton_id = False
        dossier.numero_carton = False
        
        # Mettre à jour l'état du carton
        if self.nombre_dossiers == 0:
            self.state = 'ouvert'
        elif self.state == 'plein':
            self.state = 'en_cours'
        
        self.message_post(
            body=_("Dossier %s retiré du carton") % dossier.numero_dossier,
            subtype_xmlid='mail.mt_note'
        )
    
    def action_terminer_carton(self):
        """Termine le remplissage du carton et le prépare pour la numérisation"""
        self.ensure_one()
        
        if self.state not in ['en_cours', 'plein']:
            raise UserError(_("Seuls les cartons en cours de remplissage peuvent être terminés."))
        
        if self.nombre_dossiers == 0:
            raise UserError(_("Impossible de terminer un carton vide."))
        
        self.state = 'termine'
        
        # Passer tous les dossiers du carton à l'état numérisation
        for dossier in self.dossier_ids:
            if dossier.state == 'transfert':
                dossier.action_valider_transfert()
        
        self.message_post(
            body=_("Carton terminé avec %d dossiers - Prêt pour numérisation") % self.nombre_dossiers,
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Carton Terminé'),
                'message': _('Carton %s prêt pour numérisation (%d dossiers)') % (
                    self.numero_carton, self.nombre_dossiers),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_demarrer_numerisation(self):
        """Démarre la numérisation du carton"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Seuls les cartons terminés peuvent être numérisés."))
        
        self.write({
            'state': 'numerise',
            'date_debut_numerisation': fields.Datetime.now()
        })
        
        self.message_post(
            body=_("Numérisation du carton démarrée"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_terminer_numerisation(self):
        """Termine la numérisation du carton"""
        self.ensure_one()
        
        if self.state != 'numerise':
            raise UserError(_("Le carton doit être en cours de numérisation."))
        
        if not self.date_debut_numerisation:
            raise UserError(_("Date de début de numérisation manquante."))
        
        self.date_fin_numerisation = fields.Datetime.now()
        
        self.message_post(
            body=_("Numérisation terminée en %d minutes - %d pièces numérisées") % (
                self.duree_numerisation, self.nombre_pieces_total),
            subtype_xmlid='mail.mt_comment'
        )
    
    # === ACTIONS D'INTERFACE ===
    def action_voir_dossiers(self):
        """Ouvre la vue des dossiers du carton"""
        self.ensure_one()
        
        return {
            'name': _('Dossiers du Carton %s') % self.numero_carton,
            'type': 'ir.actions.act_window',
            'res_model': 'dossier.collecteur',
            'view_mode': 'tree,form,kanban',
            'domain': [('carton_id', '=', self.id)],
            'context': {
                'default_carton_id': self.id,
                'search_default_carton_id': self.id,
            },
            'target': 'current',
        }
    
    def action_wizard_ajouter_dossiers(self):
        """Ouvre le wizard pour ajouter des dossiers"""
        self.ensure_one()
        
        return {
            'name': _('Ajouter des Dossiers au Carton'),
            'type': 'ir.actions.act_window',
            'res_model': 'carton.ajouter.dossiers.wizard',
            'view_mode': 'form',
            'context': {
                'default_carton_id': self.id,
            },
            'target': 'new',
        }
    
    # === CONTRAINTES ===
    @api.constrains('capacite_max')
    def _check_capacite_max(self):
        for record in self:
            if record.capacite_max <= 0:
                raise ValidationError(_("La capacité maximum doit être supérieure à 0."))
            if record.capacite_max > 200:
                raise ValidationError(_("La capacité maximum ne peut pas dépasser 200 dossiers."))
    
    @api.constrains('numero_carton')
    def _check_numero_carton_unique(self):
        for record in self:
            if self.search_count([('numero_carton', '=', record.numero_carton), ('id', '!=', record.id)]) > 0:
                raise ValidationError(_("Ce numéro de carton existe déjà."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            name = f"Carton {record.numero_carton}"
            if record.type_dossier:
                type_name = dict(record._fields['type_dossier'].selection)[record.type_dossier]
                name += f" ({type_name})"
            if record.nombre_dossiers:
                name += f" - {record.nombre_dossiers}/{record.capacite_max}"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = [('numero_carton', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

