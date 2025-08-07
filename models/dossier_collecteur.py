# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class DossierCollecteur(models.Model):
    _name = 'dossier.collecteur'
    _description = 'Dossier Collecteur - Workflow Complet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'numero_dossier desc'
    _rec_name = 'numero_dossier'

    # === IDENTIFICATION ===
    numero_dossier = fields.Char(
        string='N° Dossier', 
        readonly=True, 
        copy=False,
        tracking=True,
        help="Numéro unique du dossier collecteur"
    )
    date_creation = fields.Datetime(
        string='Date de Création',
        default=fields.Datetime.now,
        readonly=True,
        help="Date de création du carton"
    )
    
    date_reception = fields.Datetime(
        string='Date de Réception', 
        default=fields.Datetime.now,
        tracking=True,
        help="Date de réception du dossier"
    )
    
    type_dossier = fields.Selection([
        ('collecteur', 'Dossier Collecteur')
    ], string='Type de Dossier', default='collecteur', required=True, tracking=True)
    
    # === WORKFLOW STATES ===
    state = fields.Selection([
        ('reception', 'Réception'),
        ('traitement', 'Traitement Physique'),
        ('transfert', 'Transfert Numérisation'),
        ('numerisation', 'Numérisation'),
        ('indexation', 'Indexation'),
        ('livraison', 'Livraison Numérique'),
        ('livre', 'Livré')
    ], string='État', default='reception', tracking=True, help="État actuel du dossier dans le workflow")
    
    # === RELATIONS PRINCIPALES ===
    reception_id = fields.Many2one(
        'reception.dossier', 
        string='Réception',
        ondelete='cascade',
        required=True,
        help="Réception d'origine de ce dossier"
    )
    
    traitement_id = fields.Many2one(
        'traitement.physique', 
        string='Traitement Physique',
        help="Traitement physique associé"
    )
    
    numerisation_id = fields.Many2one(
        'numerisation.dossier', 
        string='Numérisation',
        help="Numérisation associée"
    )
    
    indexation_ids = fields.One2many(
        'indexation.dossier', 
        'dossier_id', 
        string='Indexations',
        help="Indexations des documents"
    )
    
    livraison_id = fields.Many2one(
        'livraison.numerique', 
        string='Livraison',
        help="Livraison numérique associée"
    )
    
    carton_id = fields.Many2one(
        'carton.numerisation',
        string='Carton',
        help="Carton de numérisation"
    )
    
    # === INFORMATIONS DE TRAITEMENT ===
    radical_dossier = fields.Char(
        string='Radical Dossier', 
        tracking=True,
        help="Radical du dossier saisi lors du traitement physique"
    )
    
    code_agence = fields.Char(
        string='Code Agence', 
        tracking=True,
        help="Code de l'agence d'origine"
    )
    
    numero_carton = fields.Char(
        string='N° Carton', 
        tracking=True,
        help="Numéro du carton de numérisation"
    )
    
    type_dossier_detail = fields.Selection([
        ('pret', 'Prêt'),
        ('equipement', 'Équipement'),
        ('compte', 'Compte'),
        ('evenement', 'Événement')
    ], string='Type Détaillé', tracking=True, help="Type détaillé du dossier pour la numérisation")
    
    # === RESPONSABLES PAR ÉTAPE ===
    archiviste_id = fields.Many2one(
        'res.users',
        string='Archiviste',
        related='reception_id.archiviste_id',
        help="Archiviste responsable de la réception"
    )
    
    agent_traitement_id = fields.Many2one(
        'res.users', 
        string='Agent de Traitement',
        tracking=True,
        help="Agent responsable du traitement physique"
    )
    
    gestionnaire_stock_id = fields.Many2one(
        'res.users', 
        string='Gestionnaire de Stock',
        tracking=True,
        help="Gestionnaire responsable du transfert"
    )
    
    operateur_numerisation_id = fields.Many2one(
        'res.users', 
        string='Opérateur Numérisation',
        tracking=True,
        help="Opérateur responsable de la numérisation"
    )
    
    agent_indexation_id = fields.Many2one(
        'res.users', 
        string='Agent Indexation',
        tracking=True,
        help="Agent responsable de l'indexation"
    )
    
    # === MÉTRIQUES ET DURÉES ===
    duree_traitement = fields.Float(
        string='Durée Traitement (min)', 
        compute='_compute_duree_traitement',
        store=True,
        help="Durée du traitement physique en minutes"
    )
    
    duree_numerisation = fields.Float(
        string='Durée Numérisation (min)', 
        compute='_compute_duree_numerisation',
        store=True,
        help="Durée de la numérisation en minutes"
    )
    
    duree_indexation = fields.Float(
        string='Durée Indexation (min)', 
        compute='_compute_duree_indexation',
        store=True,
        help="Durée totale d'indexation en minutes"
    )
    
    duree_totale = fields.Float(
        string='Durée Totale (heures)', 
        compute='_compute_duree_totale',
        store=True,
        help="Durée totale de traitement en heures"
    )
    
    nombre_pieces = fields.Integer(
        string='Nombre de Pièces',
        compute='_compute_nombre_pieces',
        store=True,
        help="Nombre total de pièces numérisées"
    )
    
    nombre_documents_indexes = fields.Integer(
        string='Documents Indexés',
        compute='_compute_nombre_documents_indexes',
        store=True,
        help="Nombre de documents indexés"
    )
    
    # === PROGRESSION ET STATUT ===
    progress = fields.Float(
        string='Progression (%)',
        compute='_compute_progress',
        help="Pourcentage de progression dans le workflow"
    )
    
    priorite = fields.Selection([
        ('normale', 'Normale'),
        ('urgente', 'Urgente'),
        ('critique', 'Critique')
    ], string='Priorité', default='normale', tracking=True)
    
    # === DATES DE SUIVI ===
    date_debut_traitement = fields.Datetime(
        string='Début Traitement',
        help="Date de début du traitement physique"
    )
    
    date_fin_traitement = fields.Datetime(
        string='Fin Traitement',
        help="Date de fin du traitement physique"
    )
    
    date_transfert = fields.Datetime(
        string='Date Transfert',
        help="Date du transfert vers la numérisation"
    )
    
    date_debut_numerisation = fields.Datetime(
        string='Début Numérisation',
        help="Date de début de la numérisation"
    )
    
    date_fin_numerisation = fields.Datetime(
        string='Fin Numérisation',
        help="Date de fin de la numérisation"
    )
    
    date_debut_indexation = fields.Datetime(
        string='Début Indexation',
        help="Date de début de l'indexation"
    )
    
    date_fin_indexation = fields.Datetime(
        string='Fin Indexation',
        help="Date de fin de l'indexation"
    )
    
    date_livraison = fields.Datetime(
        string='Date Livraison',
        help="Date de livraison numérique"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes générales sur le dossier"
    )
    
    observations_traitement = fields.Text(
        string='Observations Traitement',
        help="Observations lors du traitement physique"
    )
    
    observations_numerisation = fields.Text(
        string='Observations Numérisation',
        help="Observations lors de la numérisation"
    )
    
    observations_indexation = fields.Text(
        string='Observations Indexation',
        help="Observations lors de l'indexation"
    )
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
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('traitement_id.duree_traitement')
    def _compute_duree_traitement(self):
        for record in self:
            record.duree_traitement = record.traitement_id.duree_traitement if record.traitement_id else 0
    
    @api.depends('numerisation_id.duree_numerisation')
    def _compute_duree_numerisation(self):
        for record in self:
            record.duree_numerisation = record.numerisation_id.duree_numerisation if record.numerisation_id else 0
    
    @api.depends('indexation_ids.duree_indexation')
    def _compute_duree_indexation(self):
        for record in self:
            record.duree_indexation = sum(record.indexation_ids.mapped('duree_indexation'))
    
    @api.depends('duree_traitement', 'duree_numerisation', 'duree_indexation')
    def _compute_duree_totale(self):
        for record in self:
            duree_minutes = record.duree_traitement + record.duree_numerisation + record.duree_indexation
            record.duree_totale = duree_minutes / 60  # Conversion en heures
    
    @api.depends('numerisation_id.nombre_pieces')
    def _compute_nombre_pieces(self):
        for record in self:
            record.nombre_pieces = record.numerisation_id.nombre_pieces if record.numerisation_id else 0
    
    @api.depends('indexation_ids')
    def _compute_nombre_documents_indexes(self):
        for record in self:
            record.nombre_documents_indexes = len(record.indexation_ids)
    
    @api.depends('state')
    def _compute_progress(self):
        state_progress = {
            'reception': 10,
            'traitement': 25,
            'transfert': 40,
            'numerisation': 60,
            'indexation': 80,
            'livraison': 95,
            'livre': 100
        }
        for record in self:
            record.progress = state_progress.get(record.state, 0)
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        if not vals.get('numero_dossier'):
            vals['numero_dossier'] = self.env['ir.sequence'].next_by_code('dossier.collecteur') or _('New')
        return super(DossierCollecteur, self).create(vals)
    
    # === ACTIONS DU WORKFLOW ===
    def action_demarrer_traitement(self):
        """Démarre le traitement physique"""
        self.ensure_one()
        
        if self.state != 'reception':
            raise UserError(_("Seuls les dossiers en réception peuvent démarrer le traitement."))
        
        self.write({
            'state': 'traitement',
            'date_debut_traitement': fields.Datetime.now()
        })
        
        self._notify_next_operator('archivage_secondv.group_agent_traitement')
        self.message_post(
            body=_("Traitement physique démarré"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_valider_traitement(self):
        """Valide le traitement physique et passe au transfert"""
        self.ensure_one()
        
        if self.state != 'traitement':
            raise UserError(_("Seuls les dossiers en traitement peuvent être validés."))
        
        if not self.traitement_id:
            raise UserError(_("Aucun traitement physique enregistré pour ce dossier."))
        
        if not self.radical_dossier or not self.code_agence:
            raise UserError(_("Le radical dossier et le code agence sont obligatoires."))
        
        self.write({
            'state': 'transfert',
            'date_fin_traitement': fields.Datetime.now()
        })
        
        self._notify_next_operator("archivage_secondv.group_gestionnaire_stock")
        self.message_post(
            body=_("Traitement physique terminé, prêt pour transfert"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_valider_transfert(self):
        """Valide le transfert vers la numérisation"""
        self.ensure_one()
        
        if self.state != 'transfert':
            raise UserError(_("Seuls les dossiers en transfert peuvent être validés."))
        
        self.write({
            'state': 'numerisation',
            'date_transfert': fields.Datetime.now(),
            'gestionnaire_stock_id': self.env.user.id
        })
        
        self._notify_next_operator("archivage_secondv.group_operateur_numerisation")
        self.message_post(
            body=_("Dossier transféré vers la zone de numérisation"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_valider_numerisation(self):
        """Valide la numérisation et passe à l'indexation"""
        self.ensure_one()
        
        if self.state != 'numerisation':
            raise UserError(_("Seuls les dossiers en numérisation peuvent être validés."))
        
        if not self.numerisation_id:
            raise UserError(_("Aucune numérisation enregistrée pour ce dossier."))
        
        if not self.type_dossier_detail or not self.numero_carton:
            raise UserError(_("Le type de dossier et le numéro de carton sont obligatoires."))
        
        self.write({
            'state': 'indexation',
            'date_fin_numerisation': fields.Datetime.now()
        })
        
        self._notify_next_operator("archivage_secondv.group_agent_indexation")
        self.message_post(
            body=_("Numérisation terminée, prêt pour indexation"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_valider_indexation(self):
        """Valide l'indexation et passe à la livraison"""
        self.ensure_one()
        
        if self.state != 'indexation':
            raise UserError(_("Seuls les dossiers en indexation peuvent être validés."))
        
        if not self.indexation_ids:
            raise UserError(_("Aucune indexation enregistrée pour ce dossier."))
        
        self.write({
            'state': 'livraison',
            'date_fin_indexation': fields.Datetime.now()
        })
        
        self._notify_next_operator("archivage_secondv.group_archiviste")
        self.message_post(
            body=_("Indexation terminée, prêt pour livraison"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_valider_livraison(self):
        """Valide la livraison finale"""
        self.ensure_one()
        
        if self.state != 'livraison':
            raise UserError(_("Seuls les dossiers en livraison peuvent être validés."))
        
        if not self.livraison_id:
            raise UserError(_("Aucune livraison enregistrée pour ce dossier."))
        
        self.write({
            'state': 'livre',
            'date_livraison': fields.Datetime.now()
        })
        
        # Vérifier si la réception est terminée
        self.reception_id._check_completion()
        
        self.message_post(
            body=_("Dossier livré avec succès à CIH Bank"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_retour_etape_precedente(self):
        """Retourne à l'étape précédente"""
        self.ensure_one()
        
        state_sequence = ['reception', 'traitement', 'transfert', 'numerisation', 'indexation', 'livraison', 'livre']
        current_index = state_sequence.index(self.state)
        
        if current_index > 0:
            previous_state = state_sequence[current_index - 1]
            self.state = previous_state
            self.message_post(
                body=_("Dossier retourné à l'étape : %s") % dict(self._fields['state'].selection)[previous_state],
                subtype_xmlid='mail.mt_note'
            )
        else:
            raise UserError(_("Impossible de retourner en arrière depuis cette étape."))
    
    # === ACTIONS D'INTERFACE ===
    def action_creer_traitement(self):
        """Crée un nouveau traitement physique"""
        self.ensure_one()
        
        if self.state != 'traitement':
            raise UserError(_("Le dossier doit être en état 'Traitement' pour créer un traitement physique."))
        
        if self.traitement_id:
            raise UserError(_("Un traitement physique existe déjà pour ce dossier."))
        
        return {
            'name': _('Nouveau Traitement Physique'),
            'type': 'ir.actions.act_window',
            'res_model': 'traitement.physique',
            'view_mode': 'form',
            'context': {
                'default_dossier_id': self.id,
            },
            'target': 'new',
        }
    
    def action_creer_numerisation(self):
        """Crée une nouvelle numérisation"""
        self.ensure_one()
        
        if self.state != 'numerisation':
            raise UserError(_("Le dossier doit être en état 'Numérisation' pour créer une numérisation."))
        
        if self.numerisation_id:
            raise UserError(_("Une numérisation existe déjà pour ce dossier."))
        
        return {
            'name': _('Nouvelle Numérisation'),
            'type': 'ir.actions.act_window',
            'res_model': 'numerisation.dossier',
            'view_mode': 'form',
            'context': {
                'default_dossier_id': self.id,
            },
            'target': 'new',
        }
    
    def action_creer_indexation(self):
        """Crée une nouvelle indexation"""
        self.ensure_one()
        
        if self.state != 'indexation':
            raise UserError(_("Le dossier doit être en état 'Indexation' pour créer une indexation."))
        
        return {
            'name': _('Nouvelle Indexation'),
            'type': 'ir.actions.act_window',
            'res_model': 'indexation.dossier',
            'view_mode': 'form',
            'context': {
                'default_dossier_id': self.id,
            },
            'target': 'new',
        }
    
    def action_creer_livraison(self):
        """Crée une nouvelle livraison"""
        self.ensure_one()
        
        if self.state != 'livraison':
            raise UserError(_("Le dossier doit être en état 'Livraison' pour créer une livraison."))
        
        if self.livraison_id:
            raise UserError(_("Une livraison existe déjà pour ce dossier."))
        
        return {
            'name': _('Nouvelle Livraison Numérique'),
            'type': 'ir.actions.act_window',
            'res_model': 'livraison.numerique',
            'view_mode': 'form',
            'context': {
                'default_dossier_ids': [(6, 0, [self.id])],
            },
            'target': 'new',
        }
    
    # === MÉTHODES PRIVÉES ===
    def _notify_next_operator(self, group_xmlid):
        """Envoie une notification au prochain opérateur"""
        try:
            group = self.env.ref(group_xmlid)
            users = group.users
            partner_ids = users.mapped('partner_id.id')
            
            if partner_ids:
                self.message_post(
                    body=_("Nouveau dossier %s prêt pour traitement") % self.numero_dossier,
                    partner_ids=partner_ids,
                    subtype_xmlid='mail.mt_comment'
                )
        except Exception:
            # Si le groupe n'existe pas, on continue sans erreur
            pass
    
    # === CONTRAINTES ===
    @api.constrains('state')
    def _check_state_transition(self):
        """Vérifie que les transitions d'état sont valides"""
        for record in self:
            if record.state == 'traitement' and not record.reception_id:
                raise ValidationError(_("Un dossier ne peut pas être en traitement sans réception associée."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        """Personnalise l'affichage du nom"""
        result = []
        for record in self:
            name = record.numero_dossier or _('Nouveau')
            if record.radical_dossier:
                name += f" - {record.radical_dossier}"
            if record.state:
                state_name = dict(record._fields['state'].selection)[record.state]
                name += f" ({state_name})"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', '|', ('numero_dossier', operator, name), 
                   ('radical_dossier', operator, name), 
                   ('code_agence', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)



    def _notify_next_operator(self, group_xmlid):
        """Envoie une notification au prochain opérateur responsable"""
        group = self.env.ref(group_xmlid)
        if group:
            users = group.users
            if users:
                for user in users:
                    self.message_post(
                        body=_("Un nouveau dossier est prêt pour vous : %s") % self.numero_dossier,
                        partner_ids=[user.partner_id.id],
                        subtype_xmlid="mail.mt_note"
                    )



    
    # === MÉTHODES PRIVÉES ===
    def _notify_next_operator(self, group_xml_id):
        """Notifie les utilisateurs du groupe suivant"""
        try:
            group_id = self.env.ref(group_xml_id)
            if group_id:
                users = self.env["res.users"].search([("groups_id", "in", group_id.id)])
                for user in users:
                    self.message_post(
                        partner_ids=[user.partner_id.id],
                        body=_("Nouveau dossier %s en attente de traitement dans votre étape.") % self.numero_dossier,
                        subtype_xmlid='mail.mt_comment'
                    )
        except Exception:
            # Si le groupe n'existe pas, on continue sans erreur
            pass
    
    # === CONTRAINTES ===
    @api.constrains('radical_dossier')
    def _check_radical_dossier(self):
        for record in self:
            if record.radical_dossier and len(record.radical_dossier) < 3:
                raise ValidationError(_("Le radical dossier doit contenir au moins 3 caractères."))
    
    @api.constrains('code_agence')
    def _check_code_agence(self):
        for record in self:
            if record.code_agence and len(record.code_agence) < 2:
                raise ValidationError(_("Le code agence doit contenir au moins 2 caractères."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.numero_dossier}"
            if record.radical_dossier:
                name += f" - {record.radical_dossier}"
            if record.state:
                state_name = dict(record._fields['state'].selection)[record.state]
                name += f" ({state_name})"
            result.append((record.id, name))
        return result
    
    # === MÉTHODES DE RECHERCHE ===
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', '|', ('numero_dossier', operator, name), ('radical_dossier', operator, name), ('code_agence', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

