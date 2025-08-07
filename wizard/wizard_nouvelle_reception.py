# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class WizardNouvelleReception(models.TransientModel):
    _name = 'wizard.nouvelle.reception'
    _description = 'Assistant Nouvelle Réception'

    # Informations de base
    date_reception = fields.Datetime(
        string='Date de Réception',
        default=fields.Datetime.now,
        required=True
    )
    
    type_dossier = fields.Selection([
        ('collecteur', 'Dossier Collecteur'),
        ('pret', 'Dossier Prêt'),
        ('equipement', 'Dossier Équipement'),
        ('compte', 'Dossier Compte'),
        ('evenement', 'Dossier Événement'),
        ('mixte', 'Dossiers Mixtes')
    ], string='Type de Dossier', required=True, default='collecteur')
    
    nombre_dossiers = fields.Integer(
        string='Nombre de Dossiers',
        required=True,
        default=1
    )
    
    # Informations bordereau
    numero_bordereau = fields.Char(
        string='Numéro Bordereau',
        required=True
    )
    
    coursier = fields.Char(
        string='Nom du Coursier',
        required=True
    )
    
    heure_arrivee = fields.Datetime(
        string='Heure d\'Arrivée',
        default=fields.Datetime.now
    )
    
    # Options avancées
    creation_automatique_dossiers = fields.Boolean(
        string='Créer automatiquement les dossiers',
        default=True,
        help="Créer automatiquement les enregistrements de dossiers collecteurs"
    )
    
    demarrer_traitement = fields.Boolean(
        string='Démarrer le traitement immédiatement',
        default=False,
        help="Valider la réception et démarrer le traitement physique"
    )
    
    notes = fields.Text(
        string='Notes',
        placeholder="Notes sur cette réception..."
    )

    @api.constrains('nombre_dossiers')
    def _check_nombre_dossiers(self):
        for record in self:
            if record.nombre_dossiers <= 0:
                raise ValidationError(_("Le nombre de dossiers doit être supérieur à 0."))
            if record.nombre_dossiers > 1000:
                raise ValidationError(_("Le nombre de dossiers ne peut pas dépasser 1000 par réception."))

    @api.constrains('date_reception', 'heure_arrivee')
    def _check_dates(self):
        for record in self:
            if record.heure_arrivee and record.date_reception:
                if record.heure_arrivee > record.date_reception:
                    raise ValidationError(_("L'heure d'arrivée ne peut pas être postérieure à la date de réception."))

    def action_creer_reception(self):
        """Créer la réception avec les paramètres du wizard"""
        self.ensure_one()
        
        # Créer la réception
        reception_vals = {
            'date_reception': self.date_reception,
            'type_dossier': self.type_dossier,
            'nombre_dossiers': self.nombre_dossiers,
            'numero_bordereau': self.numero_bordereau,
            'coursier': self.coursier,
            'heure_arrivee': self.heure_arrivee,
            'archiviste_id': self.env.user.id,
            'notes': self.notes,
            'state': 'brouillon'
        }
        
        reception = self.env['reception.dossier'].create(reception_vals)
        
        # Créer automatiquement les dossiers si demandé
        if self.creation_automatique_dossiers:
            self._creer_dossiers_automatiquement(reception)
        
        # Démarrer le traitement si demandé
        if self.demarrer_traitement:
            reception.action_valider_reception()
            reception.action_demarrer_traitement()
        
        # Retourner l'action pour ouvrir la réception créée
        return {
            'type': 'ir.actions.act_window',
            'name': _('Réception Créée'),
            'res_model': 'reception.dossier',
            'res_id': reception.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _creer_dossiers_automatiquement(self, reception):
        """Créer automatiquement les dossiers collecteurs"""
        dossier_obj = self.env['dossier.collecteur']
        
        for i in range(self.nombre_dossiers):
            dossier_vals = {
                'reception_id': reception.id,
                'type_dossier': self.type_dossier,
                'state': 'recu'
            }
            dossier_obj.create(dossier_vals)
    
    def action_annuler(self):
        """Annuler le wizard"""
        return {'type': 'ir.actions.act_window_close'}


class WizardCreerCarton(models.TransientModel):
    _name = 'wizard.creer.carton'
    _description = 'Assistant Création Carton'

    # Informations carton
    type_dossier = fields.Selection([
        ('pret', 'Prêt'),
        ('equipement', 'Équipement'),
        ('compte', 'Compte'),
        ('evenement', 'Événement')
    ], string='Type de Dossier', required=True)
    
    capacite_max = fields.Integer(
        string='Capacité Maximum',
        default=50,
        required=True,
        help="Nombre maximum de dossiers dans ce carton"
    )
    
    operateur_id = fields.Many2one(
        'res.users',
        string='Opérateur',
        default=lambda self: self.env.user,
        required=True
    )
    
    # Options
    generer_numero_automatique = fields.Boolean(
        string='Générer numéro automatiquement',
        default=True
    )
    
    numero_carton_manuel = fields.Char(
        string='Numéro Carton (Manuel)',
        help="Laisser vide pour génération automatique"
    )
    
    demarrer_numerisation = fields.Boolean(
        string='Démarrer la numérisation immédiatement',
        default=False
    )
    
    notes = fields.Text(
        string='Notes',
        placeholder="Notes sur ce carton..."
    )

    @api.constrains('capacite_max')
    def _check_capacite_max(self):
        for record in self:
            if record.capacite_max <= 0:
                raise ValidationError(_("La capacité maximum doit être supérieure à 0."))
            if record.capacite_max > 200:
                raise ValidationError(_("La capacité maximum ne peut pas dépasser 200 dossiers."))

    @api.onchange('generer_numero_automatique')
    def _onchange_generer_numero_automatique(self):
        if self.generer_numero_automatique:
            self.numero_carton_manuel = False

    def action_creer_carton(self):
        """Créer le carton avec les paramètres du wizard"""
        self.ensure_one()
        
        # Déterminer le numéro de carton
        if self.generer_numero_automatique:
            numero_carton = self._generer_numero_carton()
        else:
            if not self.numero_carton_manuel:
                raise UserError(_("Veuillez saisir un numéro de carton ou activer la génération automatique."))
            numero_carton = self.numero_carton_manuel
        
        # Créer le carton
        carton_vals = {
            'numero_carton': numero_carton,
            'type_dossier': self.type_dossier,
            'capacite_max': self.capacite_max,
            'operateur_id': self.operateur_id.id,
            'notes': self.notes,
            'state': 'nouveau'
        }
        
        carton = self.env['carton.numerisation'].create(carton_vals)
        
        # Démarrer la numérisation si demandé
        if self.demarrer_numerisation:
            carton.action_demarrer_numerisation()
        
        # Retourner l'action pour ouvrir le carton créé
        return {
            'type': 'ir.actions.act_window',
            'name': _('Carton Créé'),
            'res_model': 'carton.numerisation',
            'res_id': carton.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _generer_numero_carton(self):
        """Générer un numéro de carton automatique"""
        sequence_code = f'carton.{self.type_dossier}'
        return self.env['ir.sequence'].next_by_code(sequence_code) or f'{self.type_dossier.upper()}001'
    
    def action_annuler(self):
        """Annuler le wizard"""
        return {'type': 'ir.actions.act_window_close'}


class WizardTransfertStock(models.TransientModel):
    _name = 'wizard.transfert.stock'
    _description = 'Assistant Transfert Stock'

    # Informations transfert
    type_transfert = fields.Selection([
        ('reception_vers_traitement', 'Réception → Traitement'),
        ('traitement_vers_numerisation', 'Traitement → Numérisation'),
        ('numerisation_vers_indexation', 'Numérisation → Indexation'),
        ('indexation_vers_livraison', 'Indexation → Livraison'),
        ('vers_quarantaine', 'Vers Quarantaine'),
        ('retour_quarantaine', 'Retour de Quarantaine')
    ], string='Type de Transfert', required=True)
    
    dossier_ids = fields.Many2many(
        'dossier.collecteur',
        string='Dossiers à Transférer',
        required=True
    )
    
    gestionnaire_id = fields.Many2one(
        'res.users',
        string='Gestionnaire',
        default=lambda self: self.env.user,
        required=True
    )
    
    date_transfert = fields.Datetime(
        string='Date de Transfert',
        default=fields.Datetime.now,
        required=True
    )
    
    # Emplacements
    emplacement_source_id = fields.Many2one(
        'stock.location',
        string='Emplacement Source',
        required=True
    )
    
    emplacement_destination_id = fields.Many2one(
        'stock.location',
        string='Emplacement Destination',
        required=True
    )
    
    # Options
    valider_automatiquement = fields.Boolean(
        string='Valider automatiquement le transfert',
        default=True
    )
    
    envoyer_notification = fields.Boolean(
        string='Envoyer notification au responsable suivant',
        default=True
    )
    
    notes = fields.Text(
        string='Notes de Transfert',
        placeholder="Notes sur ce transfert..."
    )

    @api.onchange('type_transfert')
    def _onchange_type_transfert(self):
        """Mettre à jour les emplacements selon le type de transfert"""
        if self.type_transfert:
            emplacements = self._get_emplacements_par_type()
            self.emplacement_source_id = emplacements.get('source')
            self.emplacement_destination_id = emplacements.get('destination')

    def _get_emplacements_par_type(self):
        """Retourner les emplacements source et destination selon le type"""
        emplacements_map = {
            'reception_vers_traitement': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_reception', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_traitement', False)
            },
            'traitement_vers_numerisation': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_traitement', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_numerisation', False)
            },
            'numerisation_vers_indexation': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_numerisation', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_indexation', False)
            },
            'indexation_vers_livraison': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_indexation', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_livraison', False)
            },
            'vers_quarantaine': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_traitement', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_quarantaine', False)
            },
            'retour_quarantaine': {
                'source': self.env.ref('archivage_collecteurs_complet.stock_location_zone_quarantaine', False),
                'destination': self.env.ref('archivage_collecteurs_complet.stock_location_zone_traitement', False)
            }
        }
        return emplacements_map.get(self.type_transfert, {})

    def action_effectuer_transfert(self):
        """Effectuer le transfert de stock"""
        self.ensure_one()
        
        if not self.dossier_ids:
            raise UserError(_("Veuillez sélectionner au moins un dossier à transférer."))
        
        # Créer le transfert de stock
        picking_type = self._get_picking_type()
        
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.emplacement_source_id.id,
            'location_dest_id': self.emplacement_destination_id.id,
            'scheduled_date': self.date_transfert,
            'origin': f'Transfert {self.type_transfert}',
            'note': self.notes
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Créer les lignes de transfert pour chaque dossier
        for dossier in self.dossier_ids:
            move_vals = {
                'name': f'Transfert {dossier.numero_dossier}',
                'product_id': self._get_product_dossier().id,
                'product_uom_qty': 1,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'picking_id': picking.id,
                'location_id': self.emplacement_source_id.id,
                'location_dest_id': self.emplacement_destination_id.id,
            }
            self.env['stock.move'].create(move_vals)
        
        # Valider automatiquement si demandé
        if self.valider_automatiquement:
            picking.action_confirm()
            picking.action_assign()
            picking.button_validate()
        
        # Envoyer notification si demandé
        if self.envoyer_notification:
            self._envoyer_notification_transfert(picking)
        
        # Mettre à jour l'état des dossiers
        self._mettre_a_jour_etat_dossiers()
        
        # Retourner l'action pour voir le transfert
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfert Effectué'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _get_picking_type(self):
        """Retourner le type d'opération selon le transfert"""
        picking_types_map = {
            'reception_vers_traitement': 'picking_type_vers_traitement',
            'traitement_vers_numerisation': 'picking_type_vers_numerisation',
            'numerisation_vers_indexation': 'picking_type_vers_indexation',
            'indexation_vers_livraison': 'picking_type_vers_livraison',
            'vers_quarantaine': 'picking_type_vers_quarantaine',
            'retour_quarantaine': 'picking_type_retour_quarantaine'
        }
        
        picking_type_ref = picking_types_map.get(self.type_transfert)
        if picking_type_ref:
            return self.env.ref(f'archivage_collecteurs_complet.{picking_type_ref}')
        
        # Fallback sur un type générique
        return self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
    
    def _get_product_dossier(self):
        """Retourner le produit générique pour les dossiers"""
        # Créer ou récupérer un produit générique pour les dossiers
        product = self.env['product.product'].search([('default_code', '=', 'DOSSIER_COLLECTEUR')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Dossier Collecteur',
                'default_code': 'DOSSIER_COLLECTEUR',
                'type': 'product',
                'categ_id': self.env.ref('product.product_category_all').id,
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            })
        return product
    
    def _envoyer_notification_transfert(self, picking):
        """Envoyer une notification du transfert"""
        # Logique de notification (email, message, etc.)
        pass
    
    def _mettre_a_jour_etat_dossiers(self):
        """Mettre à jour l'état des dossiers selon le transfert"""
        etat_map = {
            'reception_vers_traitement': 'en_traitement',
            'traitement_vers_numerisation': 'pret_numerisation',
            'numerisation_vers_indexation': 'pret_indexation',
            'indexation_vers_livraison': 'pret_livraison',
            'vers_quarantaine': 'en_quarantaine',
            'retour_quarantaine': 'en_traitement'
        }
        
        nouvel_etat = etat_map.get(self.type_transfert)
        if nouvel_etat:
            self.dossier_ids.write({'state': nouvel_etat})
    
    def action_annuler(self):
        """Annuler le wizard"""
        return {'type': 'ir.actions.act_window_close'}

