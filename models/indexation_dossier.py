# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class IndexationDossier(models.Model):
    _name = 'indexation.dossier'
    _description = 'Indexation des Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'heure_debut desc'
    _rec_name = 'display_name'

    # === IDENTIFICATION ===
    dossier_id = fields.Many2one(
        'dossier.collecteur', 
        string='Dossier Collecteur', 
        required=True,
        ondelete='cascade',
        help="Dossier collecteur à indexer"
    )

    agent_id = fields.Many2one(
        'res.users',
        string="Agent d'Indexation",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=lambda self: [
            ("groups_id", "in", [self.env.ref("archivage_secondv.group_agent_indexation").id])
        ],
        help="Agent responsable de l'indexation"
    )
    
    # === INFORMATIONS D'INDEXATION ===
    type_document = fields.Selection([
        ('contrat', 'Contrat'),
        ('piece_identite', 'Pièce d\'Identité'),
        ('justificatif_revenus', 'Justificatif de Revenus'),
        ('attestation', 'Attestation'),
        ('facture', 'Facture'),
        ('releve', 'Relevé'),
        ('courrier', 'Courrier'),
        ('formulaire', 'Formulaire'),
        ('autre', 'Autre')
    ], string='Type de Document', required=True, tracking=True, 
       help="Type de document indexé")
    
    numero_contrat = fields.Char(
        string='N° Contrat',
        tracking=True,
        help="Numéro de contrat si disponible"
    )
    
    numero_compte = fields.Char(
        string='N° Compte',
        tracking=True,
        help="Numéro de compte client"
    )
    
    # === MÉTADONNÉES DU DOCUMENT ===
    titre_document = fields.Char(
        string='Titre du Document',
        required=True,
        help="Titre ou description du document"
    )
    
    date_document = fields.Date(
        string='Date du Document',
        help="Date du document original"
    )
    
    auteur_document = fields.Char(
        string='Auteur/Émetteur',
        help="Auteur ou émetteur du document"
    )
    
    reference_interne = fields.Char(
        string='Référence Interne',
        help="Référence interne du document"
    )
    
    # === CLASSIFICATION ===
    categorie = fields.Selection([
        ('administratif', 'Administratif'),
        ('financier', 'Financier'),
        ('juridique', 'Juridique'),
        ('technique', 'Technique'),
        ('commercial', 'Commercial')
    ], string='Catégorie', help="Catégorie du document")
    
    confidentialite = fields.Selection([
        ('public', 'Public'),
        ('interne', 'Interne'),
        ('confidentiel', 'Confidentiel'),
        ('secret', 'Secret')
    ], string='Niveau de Confidentialité', default='interne', 
       help="Niveau de confidentialité du document")
    
    # === GESTION DU TEMPS ===
    heure_debut = fields.Datetime(
        string='Heure de Début', 
        default=fields.Datetime.now,
        readonly=True,
        help="Heure de début de l'indexation (automatique)"
    )
    
    heure_fin = fields.Datetime(
        string='Heure de Fin', 
        readonly=True,
        help="Heure de fin de l'indexation (automatique)"
    )
    
    duree_indexation = fields.Float(
        string='Durée (minutes)', 
        compute='_compute_duree_indexation',
        store=True,
        readonly=True,
        help="Durée de l'indexation en minutes (calculée automatiquement)"
    )
    
    # === MÉTRIQUES ===
    nombre_pieces_indexees = fields.Integer(
        string='Nombre de Pièces Indexées',
        default=1,
        help="Nombre de pièces indexées dans ce document"
    )
    
    nombre_pages = fields.Integer(
        string='Nombre de Pages',
        help="Nombre de pages du document"
    )
    
    # === ÉTAT DE L'INDEXATION ===
    state = fields.Selection([
        ('en_cours', 'En Cours'),
        ('pause', 'En Pause'),
        ('termine', 'Terminé'),
        ('valide', 'Validé'),
        ('erreur', 'Erreur')
    ], string='État', default='en_cours', tracking=True, help="État actuel de l'indexation")
    
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
    
    # === MOTS-CLÉS ET RECHERCHE ===
    mots_cles = fields.Char(
        string='Mots-clés',
        help="Mots-clés pour la recherche (séparés par des virgules)"
    )
    
    description = fields.Text(
        string='Description',
        help="Description détaillée du contenu du document"
    )
    
    # === CONTRÔLE QUALITÉ ===
    controle_qualite = fields.Boolean(
        string='Contrôle Qualité Effectué',
        default=False,
        help="Indique si le contrôle qualité a été effectué"
    )
    
    problemes_indexation = fields.Text(
        string='Problèmes d\'Indexation',
        help="Description des problèmes rencontrés lors de l'indexation"
    )
    
    # === INFORMATIONS TECHNIQUES ===
    chemin_fichier = fields.Char(
        string='Chemin du Fichier',
        help="Chemin d'accès au fichier numérisé"
    )
    
    taille_fichier = fields.Float(
        string='Taille Fichier (MB)',
        help="Taille du fichier en MB"
    )
    
    format_fichier = fields.Char(
        string='Format',
        help="Format du fichier (PDF, TIFF, etc.)"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes sur l'indexation"
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
        help="Nom d'affichage de l'indexation"
    )
    
    # === MÉTRIQUES DE PERFORMANCE ===
    vitesse_indexation = fields.Float(
        string='Vitesse (pièces/min)',
        compute='_compute_vitesse_indexation',
        help="Vitesse d'indexation en pièces par minute"
    )
    
    duree_effective = fields.Float(
        string='Durée Effective (min)',
        compute='_compute_duree_effective',
        help="Durée effective sans les pauses"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('heure_debut', 'heure_fin')
    def _compute_duree_indexation(self):
        for record in self:
            if record.heure_debut and record.heure_fin:
                delta = record.heure_fin - record.heure_debut
                record.duree_indexation = delta.total_seconds() / 60
            else:
                record.duree_indexation = 0
    
    @api.depends('duree_indexation', 'duree_pauses')
    def _compute_duree_effective(self):
        for record in self:
            record.duree_effective = record.duree_indexation - record.duree_pauses
    
    @api.depends('nombre_pieces_indexees', 'duree_effective')
    def _compute_vitesse_indexation(self):
        for record in self:
            if record.duree_effective > 0 and record.nombre_pieces_indexees > 0:
                record.vitesse_indexation = record.nombre_pieces_indexees / record.duree_effective
            else:
                record.vitesse_indexation = 0
    
    @api.depends('dossier_id')
    def _compute_display_name(self):
        for record in self:
            if record.dossier_id and record.titre_document:
                record.display_name = f"{record.dossier_id.numero_dossier} - {record.titre_document}"
            elif record.dossier_id and record.type_document:
                type_name = dict(record._fields['type_document'].selection)[record.type_document]
                record.display_name = f"{record.dossier_id.numero_dossier} - {type_name}"
            elif record.dossier_id:
                record.display_name = record.dossier_id.numero_dossier
            else:
                record.display_name = _('Nouvelle indexation')
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        """Démarre automatiquement le chronomètre à la création"""
        if 'heure_debut' not in vals:
            vals['heure_debut'] = fields.Datetime.now()
        
        indexation = super(IndexationDossier, self).create(vals)
        
        # Mettre à jour le dossier collecteur
        if indexation.dossier_id:
            indexation.dossier_id.write({
                'agent_indexation_id': indexation.agent_id.id,
                'date_debut_indexation': indexation.heure_debut,
            })
        
        return indexation
    
    def write(self, vals):
        """Met à jour les informations du dossier lors de la modification"""
        result = super(IndexationDossier, self).write(vals)
        
        # Mettre à jour le dossier collecteur si nécessaire
        for record in self:
            if any(field in vals for field in ['observations']):
                record.dossier_id.write({
                    'observations_indexation': record.observations,
                })
        
        return result
    
    # === ACTIONS PRINCIPALES ===
    def action_mettre_en_pause(self):
        """Met l'indexation en pause"""
        self.ensure_one()
        
        if self.state != 'en_cours':
            raise UserError(_("Seules les indexations en cours peuvent être mises en pause."))
        
        self.write({
            'state': 'pause',
            'heure_derniere_pause': fields.Datetime.now(),
            'nombre_pauses': self.nombre_pauses + 1
        })
        
        self.message_post(
            body=_("Indexation mise en pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_reprendre_indexation(self):
        """Reprend l'indexation après une pause"""
        self.ensure_one()
        
        if self.state != 'pause':
            raise UserError(_("Seules les indexations en pause peuvent être reprises."))
        
        if self.heure_derniere_pause:
            duree_pause = (fields.Datetime.now() - self.heure_derniere_pause).total_seconds() / 60
            self.duree_pauses += duree_pause
        
        self.write({
            'state': 'en_cours',
            'heure_derniere_pause': False
        })
        
        self.message_post(
            body=_("Indexation reprise après pause"),
            subtype_xmlid='mail.mt_note'
        )
    
    def action_terminer_indexation(self):
        """Termine l'indexation"""
        self.ensure_one()
        
        if self.state not in ['en_cours', 'pause']:
            raise UserError(_("Seules les indexations en cours ou en pause peuvent être terminées."))
        
        if not self.titre_document or not self.type_document:
            raise UserError(_("Veuillez remplir le titre et le type de document."))
        
        if self.nombre_pieces_indexees <= 0:
            raise UserError(_("Le nombre de pièces indexées doit être supérieur à 0."))
        
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
        self.dossier_id.date_fin_indexation = self.heure_fin
        
        self.message_post(
            body=_("Indexation terminée - %d pièces en %d minutes (vitesse: %.2f pièces/min)") % (
                self.nombre_pieces_indexees, self.duree_indexation, self.vitesse_indexation),
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Indexation Terminée'),
                'message': _('%d pièces indexées en %d minutes') % (
                    self.nombre_pieces_indexees, self.duree_indexation),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_valider_indexation(self):
        """Valide l'indexation"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Seules les indexations terminées peuvent être validées."))
        
        if not self.controle_qualite:
            raise UserError(_("Le contrôle qualité doit être effectué avant la validation."))
        
        self.state = 'valide'
        
        # Vérifier si toutes les indexations du dossier sont validées
        dossier = self.dossier_id
        indexations_non_validees = dossier.indexation_ids.filtered(lambda i: i.state != 'valide')
        
        if not indexations_non_validees:
            # Toutes les indexations sont validées, passer à l'étape suivante
            dossier.action_valider_indexation()
        
        self.message_post(
            body=_("Indexation validée"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_effectuer_controle_qualite(self):
        """Effectue le contrôle qualité"""
        self.ensure_one()
        
        if self.state != 'termine':
            raise UserError(_("Le contrôle qualité ne peut être effectué que sur les indexations terminées."))
        
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
        """Signale une erreur dans l'indexation"""
        self.ensure_one()
        
        self.state = 'erreur'
        self.message_post(
            body=_("Erreur signalée dans l'indexation"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_reprendre_indexation_terminee(self):
        """Reprend une indexation terminée pour modification"""
        self.ensure_one()
        
        if self.state not in ['termine', 'valide', 'erreur']:
            raise UserError(_("Seules les indexations terminées peuvent être reprises."))
        
        self.write({
            'heure_fin': False,
            'state': 'en_cours',
            'controle_qualite': False
        })
        
        self.message_post(
            body=_("Indexation reprise pour modification"),
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
    
    def action_historique_indexations(self):
        """Affiche l'historique des indexations de l'agent"""
        self.ensure_one()
        
        return {
            'name': _('Historique des Indexations - %s') % self.agent_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'indexation.dossier',
            'view_mode': 'tree,form',
            'domain': [('agent_id', '=', self.agent_id.id)],
            'context': {'search_default_agent_id': self.agent_id.id},
            'target': 'current',
        }
    
    def action_rechercher_documents_similaires(self):
        """Recherche des documents similaires"""
        self.ensure_one()
        
        domain = []
        if self.type_document:
            domain.append(('type_document', '=', self.type_document))
        if self.numero_contrat:
            domain.append(('numero_contrat', '=', self.numero_contrat))
        if self.numero_compte:
            domain.append(('numero_compte', '=', self.numero_compte))
        
        return {
            'name': _('Documents Similaires'),
            'type': 'ir.actions.act_window',
            'res_model': 'indexation.dossier',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }
    
    # === CONTRAINTES ===
    @api.constrains('nombre_pieces_indexees')
    def _check_nombre_pieces_indexees(self):
        for record in self:
            if record.state == 'termine' and record.nombre_pieces_indexees <= 0:
                raise ValidationError(_("Le nombre de pièces indexées doit être supérieur à 0."))
    
    @api.constrains('titre_document')
    def _check_titre_document(self):
        for record in self:
            if record.state == 'termine' and not record.titre_document:
                raise ValidationError(_("Le titre du document est obligatoire."))
    
    @api.constrains('duree_pauses')
    def _check_duree_pauses(self):
        for record in self:
            if record.duree_pauses < 0:
                raise ValidationError(_("La durée des pauses ne peut pas être négative."))
            if record.duree_indexation > 0 and record.duree_pauses > record.duree_indexation:
                raise ValidationError(_("La durée des pauses ne peut pas être supérieure à la durée totale."))
    
    @api.constrains('date_document')
    def _check_date_document(self):
        for record in self:
            if record.date_document and record.date_document > fields.Date.today():
                raise ValidationError(_("La date du document ne peut pas être dans le futur."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            if record.titre_document:
                name = f"{record.dossier_id.numero_dossier} - {record.titre_document}"
            elif record.type_document:
                type_name = dict(record._fields['type_document'].selection)[record.type_document]
                name = f"{record.dossier_id.numero_dossier} - {type_name}"
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
            args = ['|', '|', '|', '|', 
                   ('titre_document', operator, name), 
                   ('numero_contrat', operator, name),
                   ('numero_compte', operator, name),
                   ('mots_cles', operator, name),
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
        
        indexations = self.search(domain)
        
        if not indexations:
            return {
                'nombre_documents': 0,
                'duree_moyenne': 0,
                'duree_totale': 0,
                'vitesse_moyenne': 0,
                'nombre_pieces_total': 0
            }
        
        return {
            'nombre_documents': len(indexations),
            'duree_moyenne': sum(indexations.mapped('duree_effective')) / len(indexations),
            'duree_totale': sum(indexations.mapped('duree_effective')),
            'vitesse_moyenne': sum(indexations.mapped('vitesse_indexation')) / len(indexations),
            'nombre_pieces_total': sum(indexations.mapped('nombre_pieces_indexees'))
        }
    
    @api.model
    def get_statistiques_types_documents(self, date_debut=None, date_fin=None):
        """Retourne les statistiques par type de document"""
        domain = [('state', '=', 'valide')]
        
        if date_debut:
            domain.append(('heure_debut', '>=', date_debut))
        if date_fin:
            domain.append(('heure_fin', '<=', date_fin))
        
        indexations = self.search(domain)
        
        stats = {}
        for indexation in indexations:
            type_doc = indexation.type_document
            if type_doc not in stats:
                stats[type_doc] = {
                    'nombre': 0,
                    'pieces_total': 0,
                    'duree_totale': 0
                }
            
            stats[type_doc]['nombre'] += 1
            stats[type_doc]['pieces_total'] += indexation.nombre_pieces_indexees
            stats[type_doc]['duree_totale'] += indexation.duree_effective
        
        return stats

