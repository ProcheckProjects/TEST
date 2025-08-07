# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import os
import shutil


class LivraisonNumerique(models.Model):
    _name = 'livraison.numerique'
    _description = 'Livraison Numérique vers CIH Bank'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_livraison desc'
    _rec_name = 'numero_livraison'

    # === IDENTIFICATION ===
    numero_livraison = fields.Char(
        string='N° Livraison', 
        required=True,
        copy=False,
        readonly=True,
        tracking=True,
        help="Numéro unique de la livraison (généré automatiquement)"
    )
    
    date_livraison = fields.Datetime(
        string='Date de Livraison', 
        default=fields.Datetime.now,
        required=True,
        tracking=True,
        help="Date et heure de la livraison"
    )
    
    # === RELATIONS ===
    dossier_ids = fields.Many2many(
        'dossier.collecteur', 
        string='Dossiers Collecteurs',
        required=True,
        help="Dossiers collecteurs à livrer"
    )

    archiviste_id = fields.Many2one(
        'res.users',
        string='Archiviste',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        domain=lambda self: [
            ("groups_id", "in", [self.env.ref("archivage_secondv.group_archiviste").id])
        ],
        help="Archiviste responsable de la livraison"
    )
    
    # === INFORMATIONS DE LIVRAISON ===
    type_livraison = fields.Selection([
        ('ftp', 'Transfert FTP'),
        ('partage_securise', 'Dossier Partagé Sécurisé'),
        ('email', 'Email Sécurisé'),
        ('support_physique', 'Support Physique')
    ], string='Type de Livraison', default='partage_securise', required=True, 
       tracking=True, help="Mode de livraison utilisé")
    
    destinataire = fields.Char(
        string='Destinataire',
        default='CIH Bank',
        required=True,
        help="Destinataire de la livraison"
    )
    
    # === ÉTAT DE LA LIVRAISON ===
    state = fields.Selection([
        ('preparation', 'En Préparation'),
        ('verification', 'Vérification'),
        ('pret', 'Prêt à Livrer'),
        ('en_cours', 'En Cours de Livraison'),
        ('livre', 'Livré'),
        ('confirme', 'Confirmé par Destinataire'),
        ('erreur', 'Erreur')
    ], string='État', default='preparation', tracking=True, help="État actuel de la livraison")
    
    # === MÉTRIQUES ===
    nombre_dossiers = fields.Integer(
        string='Nombre de Dossiers',
        compute='_compute_nombre_dossiers',
        store=True,
        help="Nombre total de dossiers dans la livraison"
    )
    
    nombre_pieces_total = fields.Integer(
        string='Nombre Total de Pièces',
        compute='_compute_nombre_pieces_total',
        store=True,
        help="Nombre total de pièces dans tous les dossiers"
    )
    
    taille_totale = fields.Float(
        string='Taille Totale (MB)',
        compute='_compute_taille_totale',
        help="Taille totale des fichiers à livrer"
    )
    
    # === INFORMATIONS TECHNIQUES ===
    chemin_dossier_partage = fields.Char(
        string='Chemin Dossier Partagé',
        help="Chemin vers le dossier de partage sécurisé"
    )
    
    url_telechargement = fields.Char(
        string='URL de Téléchargement',
        help="URL de téléchargement pour le destinataire"
    )
    
    mot_de_passe = fields.Char(
        string='Mot de Passe',
        help="Mot de passe pour l'accès sécurisé"
    )
    
    date_expiration = fields.Datetime(
        string='Date d\'Expiration',
        help="Date d'expiration de l'accès"
    )
    
    # === SUIVI DE LA LIVRAISON ===
    date_preparation = fields.Datetime(
        string='Date de Préparation',
        help="Date de début de préparation"
    )
    
    date_verification = fields.Datetime(
        string='Date de Vérification',
        help="Date de vérification finale"
    )
    
    date_envoi = fields.Datetime(
        string='Date d\'Envoi',
        help="Date d'envoi effectif"
    )
    
    date_confirmation = fields.Datetime(
        string='Date de Confirmation',
        help="Date de confirmation de réception par le destinataire"
    )
    
    # === CONTRÔLE QUALITÉ ===
    verification_completude = fields.Boolean(
        string='Vérification Complétude',
        default=False,
        help="Vérification que tous les dossiers sont complets"
    )
    
    verification_qualite = fields.Boolean(
        string='Vérification Qualité',
        default=False,
        help="Vérification de la qualité des fichiers"
    )
    
    verification_nomenclature = fields.Boolean(
        string='Vérification Nomenclature',
        default=False,
        help="Vérification de la nomenclature des fichiers"
    )
    
    # === NOTIFICATIONS ===
    notification_envoyee = fields.Boolean(
        string='Notification Envoyée',
        default=False,
        help="Notification envoyée au destinataire"
    )
    
    email_destinataire = fields.Char(
        string='Email Destinataire',
        help="Adresse email du destinataire pour notification"
    )
    
    # === NOTES ET OBSERVATIONS ===
    notes = fields.Text(
        string='Notes',
        help="Notes sur la livraison"
    )
    
    observations = fields.Text(
        string='Observations',
        help="Observations particulières"
    )
    
    problemes_rencontres = fields.Text(
        string='Problèmes Rencontrés',
        help="Description des problèmes rencontrés"
    )
    
    # === HISTORIQUE ===
    historique_etats = fields.Text(
        string='Historique des États',
        readonly=True,
        help="Historique des changements d'état"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('dossier_ids')
    def _compute_nombre_dossiers(self):
        for record in self:
            record.nombre_dossiers = len(record.dossier_ids)
    
    @api.depends('dossier_ids.nombre_pieces')
    def _compute_nombre_pieces_total(self):
        for record in self:
            record.nombre_pieces_total = sum(record.dossier_ids.mapped('nombre_pieces'))
    
    @api.depends('dossier_ids')
    def _compute_taille_totale(self):
        for record in self:
            # Calcul approximatif basé sur le nombre de pièces
            # En réalité, cela devrait être calculé à partir des fichiers réels
            taille_moyenne_par_piece = 0.5  # MB par pièce (estimation)
            record.taille_totale = record.nombre_pieces_total * taille_moyenne_par_piece
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        if not vals.get('numero_livraison'):
            vals['numero_livraison'] = self.env['ir.sequence'].next_by_code('livraison.numerique') or _('New')
        
        # Initialiser l'historique
        vals['historique_etats'] = f"{fields.Datetime.now()}: Création de la livraison\n"
        
        return super(LivraisonNumerique, self).create(vals)
    
    def write(self, vals):
        # Enregistrer les changements d'état dans l'historique
        if 'state' in vals:
            for record in self:
                ancien_etat = dict(record._fields['state'].selection)[record.state]
                nouvel_etat = dict(record._fields['state'].selection)[vals['state']]
                historique = record.historique_etats or ""
                historique += f"{fields.Datetime.now()}: {ancien_etat} → {nouvel_etat}\n"
                vals['historique_etats'] = historique
        
        return super(LivraisonNumerique, self).write(vals)
    
    # === ACTIONS PRINCIPALES ===
    def action_demarrer_preparation(self):
        """Démarre la préparation de la livraison"""
        self.ensure_one()
        
        if self.state != 'preparation':
            raise UserError(_("La livraison doit être en état 'Préparation'."))
        
        if not self.dossier_ids:
            raise UserError(_("Aucun dossier sélectionné pour la livraison."))
        
        # Vérifier que tous les dossiers sont prêts
        dossiers_non_prets = self.dossier_ids.filtered(lambda d: d.state != 'livraison')
        if dossiers_non_prets:
            raise UserError(_("Certains dossiers ne sont pas prêts pour la livraison : %s") % 
                          ', '.join(dossiers_non_prets.mapped('numero_dossier')))
        
        self.write({
            'state': 'verification',
            'date_preparation': fields.Datetime.now()
        })
        
        self.message_post(
            body=_("Préparation de la livraison démarrée - %d dossiers") % self.nombre_dossiers,
            subtype_xmlid='mail.mt_note'
        )
    
    def action_effectuer_verifications(self):
        """Effectue les vérifications de qualité"""
        self.ensure_one()
        
        if self.state != 'verification':
            raise UserError(_("La livraison doit être en état 'Vérification'."))
        
        # Marquer toutes les vérifications comme effectuées
        self.write({
            'verification_completude': True,
            'verification_qualite': True,
            'verification_nomenclature': True,
            'date_verification': fields.Datetime.now()
        })
        
        self.message_post(
            body=_("Vérifications de qualité effectuées"),
            subtype_xmlid='mail.mt_note'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Vérifications Terminées'),
                'message': _('Toutes les vérifications ont été effectuées avec succès'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_valider_pour_livraison(self):
        """Valide la livraison pour envoi"""
        self.ensure_one()
        
        if self.state != 'verification':
            raise UserError(_("La livraison doit être en état 'Vérification'."))
        
        if not (self.verification_completude and self.verification_qualite and self.verification_nomenclature):
            raise UserError(_("Toutes les vérifications doivent être effectuées avant la validation."))
        
        self.state = 'pret'
        
        self.message_post(
            body=_("Livraison validée et prête pour envoi"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_effectuer_livraison(self):
        """Effectue la livraison effective"""
        self.ensure_one()
        
        if self.state != 'pret':
            raise UserError(_("La livraison doit être prête pour envoi."))
        
        try:
            self.state = 'en_cours'
            
            # Simuler la livraison selon le type
            if self.type_livraison == 'partage_securise':
                self._livrer_via_partage_securise()
            elif self.type_livraison == 'ftp':
                self._livrer_via_ftp()
            elif self.type_livraison == 'email':
                self._livrer_via_email()
            else:
                self._livrer_support_physique()
            
            self.write({
                'state': 'livre',
                'date_envoi': fields.Datetime.now()
            })
            
            # Mettre à jour les dossiers
            for dossier in self.dossier_ids:
                dossier.write({
                    'state': 'livre',
                    'livraison_id': self.id,
                    'date_livraison': self.date_envoi
                })
            
            # Envoyer notification
            self._envoyer_notification_livraison()
            
            self.message_post(
                body=_("Livraison effectuée avec succès vers %s") % self.destinataire,
                subtype_xmlid='mail.mt_comment'
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Livraison Effectuée'),
                    'message': _('Livraison %s effectuée avec succès') % self.numero_livraison,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            self.write({
                'state': 'erreur',
                'problemes_rencontres': str(e)
            })
            
            self.message_post(
                body=_("Erreur lors de la livraison : %s") % str(e),
                subtype_xmlid='mail.mt_comment'
            )
            
            raise UserError(_("Erreur lors de la livraison : %s") % str(e))
    
    def action_confirmer_reception(self):
        """Confirme la réception par le destinataire"""
        self.ensure_one()
        
        if self.state != 'livre':
            raise UserError(_("La livraison doit être livrée pour être confirmée."))
        
        self.write({
            'state': 'confirme',
            'date_confirmation': fields.Datetime.now()
        })
        
        self.message_post(
            body=_("Réception confirmée par le destinataire"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_signaler_erreur(self):
        """Signale une erreur dans la livraison"""
        self.ensure_one()
        
        self.state = 'erreur'
        self.message_post(
            body=_("Erreur signalée dans la livraison"),
            subtype_xmlid='mail.mt_comment'
        )
    
    def action_relancer_livraison(self):
        """Relance la livraison après correction d'erreur"""
        self.ensure_one()
        
        if self.state != 'erreur':
            raise UserError(_("Seules les livraisons en erreur peuvent être relancées."))
        
        self.write({
            'state': 'pret',
            'problemes_rencontres': False
        })
        
        self.message_post(
            body=_("Livraison relancée après correction"),
            subtype_xmlid='mail.mt_note'
        )
    
    # === MÉTHODES PRIVÉES DE LIVRAISON ===
    def _livrer_via_partage_securise(self):
        """Livraison via dossier partagé sécurisé"""
        self.ensure_one()
        
        # Générer un chemin unique
        import uuid
        chemin_unique = f"/partage_securise/livraison_{uuid.uuid4().hex[:8]}"
        
        # Générer un mot de passe
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        mot_de_passe = ''.join(secrets.choice(alphabet) for i in range(12))
        
        # Définir la date d'expiration (7 jours)
        date_expiration = fields.Datetime.now() + timedelta(days=7)
        
        self.write({
            'chemin_dossier_partage': chemin_unique,
            'mot_de_passe': mot_de_passe,
            'date_expiration': date_expiration,
            'url_telechargement': f"https://partage.cih.ma{chemin_unique}"
        })
        
        # Ici, on simule la création du dossier et la copie des fichiers
        # En réalité, il faudrait implémenter la logique de copie des fichiers
        
    def _livrer_via_ftp(self):
        """Livraison via FTP"""
        self.ensure_one()
        
        # Simuler le transfert FTP
        # En réalité, il faudrait implémenter la connexion FTP et le transfert
        
        self.url_telechargement = "ftp://ftp.cih.ma/livraisons/" + self.numero_livraison
        
    def _livrer_via_email(self):
        """Livraison via email sécurisé"""
        self.ensure_one()
        
        # Simuler l'envoi par email
        # En réalité, il faudrait implémenter l'envoi d'email avec pièces jointes
        
        pass
    
    def _livrer_support_physique(self):
        """Préparation pour livraison sur support physique"""
        self.ensure_one()
        
        # Simuler la préparation du support physique
        # En réalité, il faudrait graver les fichiers sur DVD/USB
        
        pass
    
    def _envoyer_notification_livraison(self):
        """Envoie une notification de livraison"""
        self.ensure_one()
        
        if not self.email_destinataire:
            return
        
        # Simuler l'envoi de notification
        # En réalité, il faudrait envoyer un email avec les détails d'accès
        
        self.notification_envoyee = True
    
    # === ACTIONS D'INTERFACE ===
    def action_voir_dossiers(self):
        """Ouvre la vue des dossiers de la livraison"""
        self.ensure_one()
        
        return {
            'name': _('Dossiers de la Livraison %s') % self.numero_livraison,
            'type': 'ir.actions.act_window',
            'res_model': 'dossier.collecteur',
            'view_mode': 'tree,form,kanban',
            'domain': [('id', 'in', self.dossier_ids.ids)],
            'target': 'current',
        }
    
    def action_generer_rapport_livraison(self):
        """Génère un rapport de livraison"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'archivage_collecteurs_complet.rapport_livraison',
            'report_type': 'qweb-pdf',
            'data': {'ids': [self.id]},
            'context': self.env.context,
        }
    
    # === CONTRAINTES ===
    @api.constrains('dossier_ids')
    def _check_dossiers_ids(self):
        for record in self:
            if not record.dossier_ids:
                raise ValidationError(_("Au moins un dossier doit être sélectionné pour la livraison."))
    
    @api.constrains('date_expiration')
    def _check_date_expiration(self):
        for record in self:
            if record.date_expiration and record.date_expiration <= fields.Datetime.now():
                raise ValidationError(_("La date d'expiration doit être dans le futur."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            name = record.numero_livraison
            if record.destinataire:
                name += f" → {record.destinataire}"
            if record.nombre_dossiers:
                name += f" ({record.nombre_dossiers} dossiers)"
            if record.state:
                state_name = dict(record._fields['state'].selection)[record.state]
                name += f" - {state_name}"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', ('numero_livraison', operator, name), 
                   ('destinataire', operator, name)] + args
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
    
    # === MÉTHODES DE REPORTING ===
    @api.model
    def get_statistiques_livraisons(self, date_debut=None, date_fin=None):
        """Retourne les statistiques des livraisons"""
        domain = []
        
        if date_debut:
            domain.append(('date_livraison', '>=', date_debut))
        if date_fin:
            domain.append(('date_livraison', '<=', date_fin))
        
        livraisons = self.search(domain)
        
        stats = {
            'nombre_livraisons': len(livraisons),
            'nombre_dossiers_total': sum(livraisons.mapped('nombre_dossiers')),
            'nombre_pieces_total': sum(livraisons.mapped('nombre_pieces_total')),
            'taille_totale': sum(livraisons.mapped('taille_totale')),
            'livraisons_par_etat': {},
            'livraisons_par_type': {}
        }
        
        # Statistiques par état
        for etat in ['preparation', 'verification', 'pret', 'en_cours', 'livre', 'confirme', 'erreur']:
            count = len(livraisons.filtered(lambda l: l.state == etat))
            if count > 0:
                stats['livraisons_par_etat'][etat] = count
        
        # Statistiques par type
        for type_liv in ['ftp', 'partage_securise', 'email', 'support_physique']:
            count = len(livraisons.filtered(lambda l: l.type_livraison == type_liv))
            if count > 0:
                stats['livraisons_par_type'][type_liv] = count
        
        return stats

