# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta


class ReportingKPI(models.Model):
    _name = 'reporting.kpi'
    _description = 'Reporting et KPIs Archivage Collecteurs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_rapport desc'
    _rec_name = 'nom_rapport'

    # === IDENTIFICATION ===
    nom_rapport = fields.Char(
        string='Nom du Rapport',
        required=True,
        help="Nom du rapport KPI"
    )
    
    date_rapport = fields.Date(
        string='Date du Rapport',
        default=fields.Date.today,
        required=True,
        help="Date de génération du rapport"
    )
    
    # === PÉRIODE D'ANALYSE ===
    periode_type = fields.Selection([
        ('quotidien', 'Quotidien'),
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
        ('annuel', 'Annuel'),
        ('personnalise', 'Période Personnalisée')
    ], string='Type de Période', required=True, default='mensuel',
       help="Type de période pour l'analyse")
    
    date_debut = fields.Date(
        string='Date de Début',
        required=True,
        help="Date de début de la période d'analyse"
    )
    
    date_fin = fields.Date(
        string='Date de Fin',
        required=True,
        help="Date de fin de la période d'analyse"
    )
    
    # === KPIs RÉCEPTION ===
    nb_dossiers_receptionnes = fields.Integer(
        string='Dossiers Réceptionnés',
        compute='_compute_kpis_reception',
        store=True,
        help="Nombre de dossiers réceptionnés dans la période"
    )
    
    nb_receptions_total = fields.Integer(
        string='Nombre de Réceptions',
        compute='_compute_kpis_reception',
        store=True,
        help="Nombre total de réceptions dans la période"
    )
    
    moyenne_dossiers_par_reception = fields.Float(
        string='Moyenne Dossiers/Réception',
        compute='_compute_kpis_reception',
        store=True,
        help="Nombre moyen de dossiers par réception"
    )
    
    # === KPIs TRAITEMENT PHYSIQUE ===
    nb_dossiers_traites = fields.Integer(
        string='Dossiers Traités',
        compute='_compute_kpis_traitement',
        store=True,
        help="Nombre de dossiers traités physiquement"
    )
    
    duree_moyenne_traitement = fields.Float(
        string='Durée Moyenne Traitement (min)',
        compute='_compute_kpis_traitement',
        store=True,
        help="Durée moyenne de traitement par dossier en minutes"
    )
    
    duree_totale_traitement = fields.Float(
        string='Durée Totale Traitement (h)',
        compute='_compute_kpis_traitement',
        store=True,
        help="Durée totale de traitement en heures"
    )
    
    # === KPIs NUMÉRISATION ===
    nb_dossiers_numerises = fields.Integer(
        string='Dossiers Numérisés',
        compute='_compute_kpis_numerisation',
        store=True,
        help="Nombre de dossiers numérisés par jour"
    )
    
    nb_pieces_numerisees = fields.Integer(
        string='Pièces Numérisées',
        compute='_compute_kpis_numerisation',
        store=True,
        help="Nombre total de pièces numérisées"
    )
    
    duree_moyenne_numerisation = fields.Float(
        string='Durée Moyenne Numérisation (min)',
        compute='_compute_kpis_numerisation',
        store=True,
        help="Durée moyenne de numérisation par dossier"
    )
    
    vitesse_moyenne_numerisation = fields.Float(
        string='Vitesse Moyenne (pièces/min)',
        compute='_compute_kpis_numerisation',
        store=True,
        help="Vitesse moyenne de numérisation"
    )
    
    # === KPIs INDEXATION ===
    nb_pieces_indexees = fields.Integer(
        string='Pièces Indexées',
        compute='_compute_kpis_indexation',
        store=True,
        help="Nombre de pièces indexées"
    )
    
    nb_documents_indexes = fields.Integer(
        string='Documents Indexés',
        compute='_compute_kpis_indexation',
        store=True,
        help="Nombre de documents indexés"
    )
    
    duree_moyenne_indexation = fields.Float(
        string='Durée Moyenne Indexation (min)',
        compute='_compute_kpis_indexation',
        store=True,
        help="Durée moyenne d'indexation par document"
    )
    
    vitesse_moyenne_indexation = fields.Float(
        string='Vitesse Moyenne Indexation (pièces/min)',
        compute='_compute_kpis_indexation',
        store=True,
        help="Vitesse moyenne d'indexation"
    )
    
    # === KPIs LIVRAISON ===
    nb_receptions_livrees = fields.Integer(
        string='Réceptions Livrées',
        compute='_compute_kpis_livraison',
        store=True,
        help="Nombre de réceptions livrées"
    )
    
    nb_dossiers_livres = fields.Integer(
        string='Dossiers Livrés',
        compute='_compute_kpis_livraison',
        store=True,
        help="Nombre de dossiers livrés"
    )
    
    nb_livraisons_effectuees = fields.Integer(
        string='Livraisons Effectuées',
        compute='_compute_kpis_livraison',
        store=True,
        help="Nombre de livraisons effectuées"
    )
    
    # === TAUX D'ERREURS ET QUALITÉ ===
    taux_erreurs = fields.Float(
        string='Taux d\'Erreurs (%)',
        compute='_compute_taux_erreurs',
        store=True,
        help="Taux d'erreurs mensuel"
    )
    
    nb_erreurs_traitement = fields.Integer(
        string='Erreurs Traitement',
        compute='_compute_taux_erreurs',
        store=True,
        help="Nombre d'erreurs en traitement"
    )
    
    nb_erreurs_numerisation = fields.Integer(
        string='Erreurs Numérisation',
        compute='_compute_taux_erreurs',
        store=True,
        help="Nombre d'erreurs en numérisation"
    )
    
    nb_erreurs_indexation = fields.Integer(
        string='Erreurs Indexation',
        compute='_compute_taux_erreurs',
        store=True,
        help="Nombre d'erreurs en indexation"
    )
    
    nb_erreurs_livraison = fields.Integer(
        string='Erreurs Livraison',
        compute='_compute_taux_erreurs',
        store=True,
        help="Nombre d'erreurs en livraison"
    )
    
    # === PERFORMANCE PAR AGENT ===
    performance_agents = fields.Text(
        string='Performance par Agent',
        compute='_compute_performance_agents',
        help="Détail des performances par agent (JSON)"
    )
    
    # === TENDANCES ===
    evolution_reception = fields.Float(
        string='Évolution Réception (%)',
        compute='_compute_tendances',
        help="Évolution par rapport à la période précédente"
    )
    
    evolution_traitement = fields.Float(
        string='Évolution Traitement (%)',
        compute='_compute_tendances',
        help="Évolution du traitement par rapport à la période précédente"
    )
    
    evolution_numerisation = fields.Float(
        string='Évolution Numérisation (%)',
        compute='_compute_tendances',
        help="Évolution de la numérisation par rapport à la période précédente"
    )
    
    # === INFORMATIONS COMPLÉMENTAIRES ===
    utilisateur_id = fields.Many2one(
        'res.users',
        string='Généré par',
        default=lambda self: self.env.user,
        help="Utilisateur ayant généré le rapport"
    )
    
    notes = fields.Text(
        string='Notes',
        help="Notes sur le rapport"
    )
    
    # === MÉTHODES DE CALCUL DES KPIs ===
    @api.depends('date_debut', 'date_fin')
    def _compute_kpis_reception(self):
        for record in self:
            domain = [
                ('date_reception', '>=', record.date_debut),
                ('date_reception', '<=', record.date_fin),
                ('state', 'in', ['valide', 'en_cours', 'termine'])
            ]
            
            receptions = self.env['reception.dossier'].search(domain)
            
            record.nb_receptions_total = len(receptions)
            record.nb_dossiers_receptionnes = sum(receptions.mapped('nombre_dossiers'))
            
            if record.nb_receptions_total > 0:
                record.moyenne_dossiers_par_reception = record.nb_dossiers_receptionnes / record.nb_receptions_total
            else:
                record.moyenne_dossiers_par_reception = 0
    
    @api.depends('date_debut', 'date_fin')
    def _compute_kpis_traitement(self):
        for record in self:
            domain = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'valide')
            ]
            
            traitements = self.env['traitement.physique'].search(domain)
            
            record.nb_dossiers_traites = len(traitements)
            
            if traitements:
                durees_effectives = traitements.mapped('duree_effective')
                record.duree_moyenne_traitement = sum(durees_effectives) / len(durees_effectives)
                record.duree_totale_traitement = sum(durees_effectives) / 60  # Conversion en heures
            else:
                record.duree_moyenne_traitement = 0
                record.duree_totale_traitement = 0
    
    @api.depends('date_debut', 'date_fin')
    def _compute_kpis_numerisation(self):
        for record in self:
            domain = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'valide')
            ]
            
            numerisations = self.env['numerisation.dossier'].search(domain)
            
            record.nb_dossiers_numerises = len(numerisations)
            record.nb_pieces_numerisees = sum(numerisations.mapped('nombre_pieces'))
            
            if numerisations:
                durees_effectives = numerisations.mapped('duree_effective')
                vitesses = numerisations.mapped('vitesse_numerisation')
                
                record.duree_moyenne_numerisation = sum(durees_effectives) / len(durees_effectives)
                record.vitesse_moyenne_numerisation = sum(vitesses) / len(vitesses)
            else:
                record.duree_moyenne_numerisation = 0
                record.vitesse_moyenne_numerisation = 0
    
    @api.depends('date_debut', 'date_fin')
    def _compute_kpis_indexation(self):
        for record in self:
            domain = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'valide')
            ]
            
            indexations = self.env['indexation.dossier'].search(domain)
            
            record.nb_documents_indexes = len(indexations)
            record.nb_pieces_indexees = sum(indexations.mapped('nombre_pieces_indexees'))
            
            if indexations:
                durees_effectives = indexations.mapped('duree_effective')
                vitesses = indexations.mapped('vitesse_indexation')
                
                record.duree_moyenne_indexation = sum(durees_effectives) / len(durees_effectives)
                record.vitesse_moyenne_indexation = sum(vitesses) / len(vitesses)
            else:
                record.duree_moyenne_indexation = 0
                record.vitesse_moyenne_indexation = 0
    
    @api.depends('date_debut', 'date_fin')
    def _compute_kpis_livraison(self):
        for record in self:
            # Réceptions livrées
            domain_receptions = [
                ('date_reception', '>=', record.date_debut),
                ('date_reception', '<=', record.date_fin),
                ('state', '=', 'termine')
            ]
            receptions_livrees = self.env['reception.dossier'].search(domain_receptions)
            record.nb_receptions_livrees = len(receptions_livrees)
            
            # Dossiers livrés
            domain_dossiers = [
                ('date_livraison', '>=', record.date_debut),
                ('date_livraison', '<=', record.date_fin),
                ('state', '=', 'livre')
            ]
            dossiers_livres = self.env['dossier.collecteur'].search(domain_dossiers)
            record.nb_dossiers_livres = len(dossiers_livres)
            
            # Livraisons effectuées
            domain_livraisons = [
                ('date_livraison', '>=', record.date_debut),
                ('date_livraison', '<=', record.date_fin),
                ('state', 'in', ['livre', 'confirme'])
            ]
            livraisons = self.env['livraison.numerique'].search(domain_livraisons)
            record.nb_livraisons_effectuees = len(livraisons)
    
    @api.depends('date_debut', 'date_fin')
    def _compute_taux_erreurs(self):
        for record in self:
            # Erreurs de traitement
            domain_traitement = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'erreur')
            ]
            record.nb_erreurs_traitement = self.env['traitement.physique'].search_count(domain_traitement)
            
            # Erreurs de numérisation
            domain_numerisation = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'erreur')
            ]
            record.nb_erreurs_numerisation = self.env['numerisation.dossier'].search_count(domain_numerisation)
            
            # Erreurs d'indexation
            domain_indexation = [
                ('heure_debut', '>=', record.date_debut),
                ('heure_fin', '<=', record.date_fin),
                ('state', '=', 'erreur')
            ]
            record.nb_erreurs_indexation = self.env['indexation.dossier'].search_count(domain_indexation)
            
            # Erreurs de livraison
            domain_livraison = [
                ('date_livraison', '>=', record.date_debut),
                ('date_livraison', '<=', record.date_fin),
                ('state', '=', 'erreur')
            ]
            record.nb_erreurs_livraison = self.env['livraison.numerique'].search_count(domain_livraison)
            
            # Calcul du taux d'erreurs global
            total_erreurs = (record.nb_erreurs_traitement + record.nb_erreurs_numerisation + 
                           record.nb_erreurs_indexation + record.nb_erreurs_livraison)
            
            total_operations = (record.nb_dossiers_traites + record.nb_dossiers_numerises + 
                              record.nb_documents_indexes + record.nb_livraisons_effectuees)
            
            if total_operations > 0:
                record.taux_erreurs = (total_erreurs / total_operations) * 100
            else:
                record.taux_erreurs = 0
    
    @api.depends('date_debut', 'date_fin')
    def _compute_performance_agents(self):
        for record in self:
            import json
            
            performance = {}
            
            # Performance agents de traitement
            agents_traitement = self.env['res.users'].search([
                ('groups_id.name', 'ilike', 'Agent de Traitement')
            ])
            
            for agent in agents_traitement:
                kpis = self.env['traitement.physique'].get_kpi_agent(
                    agent.id, record.date_debut, record.date_fin
                )
                if kpis['nombre_dossiers'] > 0:
                    performance[f"traitement_{agent.name}"] = kpis
            
            # Performance opérateurs numérisation
            operateurs = self.env['res.users'].search([
                ('groups_id.name', 'ilike', 'Opérateur Numérisation')
            ])
            
            for operateur in operateurs:
                kpis = self.env['numerisation.dossier'].get_kpi_operateur(
                    operateur.id, record.date_debut, record.date_fin
                )
                if kpis['nombre_dossiers'] > 0:
                    performance[f"numerisation_{operateur.name}"] = kpis
            
            # Performance agents indexation
            agents_indexation = self.env['res.users'].search([
                ('groups_id.name', 'ilike', 'Agent Indexation')
            ])
            
            for agent in agents_indexation:
                kpis = self.env['indexation.dossier'].get_kpi_agent(
                    agent.id, record.date_debut, record.date_fin
                )
                if kpis['nombre_documents'] > 0:
                    performance[f"indexation_{agent.name}"] = kpis
            
            record.performance_agents = json.dumps(performance, indent=2)
    
    @api.depends('date_debut', 'date_fin', 'periode_type')
    def _compute_tendances(self):
        for record in self:
            # Calculer la période précédente
            if record.periode_type == 'quotidien':
                date_debut_precedente = record.date_debut - timedelta(days=1)
                date_fin_precedente = record.date_fin - timedelta(days=1)
            elif record.periode_type == 'hebdomadaire':
                date_debut_precedente = record.date_debut - timedelta(weeks=1)
                date_fin_precedente = record.date_fin - timedelta(weeks=1)
            elif record.periode_type == 'mensuel':
                date_debut_precedente = record.date_debut - relativedelta(months=1)
                date_fin_precedente = record.date_fin - relativedelta(months=1)
            else:
                # Pour les autres types, utiliser la même durée
                duree = (record.date_fin - record.date_debut).days
                date_debut_precedente = record.date_debut - timedelta(days=duree)
                date_fin_precedente = record.date_debut - timedelta(days=1)
            
            # Créer un rapport temporaire pour la période précédente
            rapport_precedent = self.new({
                'date_debut': date_debut_precedente,
                'date_fin': date_fin_precedente,
                'periode_type': record.periode_type
            })
            
            # Calculer les évolutions
            if rapport_precedent.nb_dossiers_receptionnes > 0:
                record.evolution_reception = ((record.nb_dossiers_receptionnes - rapport_precedent.nb_dossiers_receptionnes) / 
                                            rapport_precedent.nb_dossiers_receptionnes) * 100
            else:
                record.evolution_reception = 0
            
            if rapport_precedent.nb_dossiers_traites > 0:
                record.evolution_traitement = ((record.nb_dossiers_traites - rapport_precedent.nb_dossiers_traites) / 
                                             rapport_precedent.nb_dossiers_traites) * 100
            else:
                record.evolution_traitement = 0
            
            if rapport_precedent.nb_dossiers_numerises > 0:
                record.evolution_numerisation = ((record.nb_dossiers_numerises - rapport_precedent.nb_dossiers_numerises) / 
                                               rapport_precedent.nb_dossiers_numerises) * 100
            else:
                record.evolution_numerisation = 0
    
    # === MÉTHODES CRUD ===
    @api.model
    def create(self, vals):
        # Définir automatiquement les dates selon le type de période
        if vals.get('periode_type') and not vals.get('date_debut'):
            vals.update(self._get_dates_periode(vals['periode_type']))
        
        return super(ReportingKPI, self).create(vals)
    
    def _get_dates_periode(self, periode_type):
        """Retourne les dates de début et fin selon le type de période"""
        aujourd_hui = fields.Date.today()
        
        if periode_type == 'quotidien':
            return {
                'date_debut': aujourd_hui,
                'date_fin': aujourd_hui
            }
        elif periode_type == 'hebdomadaire':
            debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
            fin_semaine = debut_semaine + timedelta(days=6)
            return {
                'date_debut': debut_semaine,
                'date_fin': fin_semaine
            }
        elif periode_type == 'mensuel':
            debut_mois = aujourd_hui.replace(day=1)
            fin_mois = (debut_mois + relativedelta(months=1)) - timedelta(days=1)
            return {
                'date_debut': debut_mois,
                'date_fin': fin_mois
            }
        elif periode_type == 'trimestriel':
            mois_actuel = aujourd_hui.month
            trimestre = ((mois_actuel - 1) // 3) + 1
            debut_trimestre = aujourd_hui.replace(month=(trimestre - 1) * 3 + 1, day=1)
            fin_trimestre = (debut_trimestre + relativedelta(months=3)) - timedelta(days=1)
            return {
                'date_debut': debut_trimestre,
                'date_fin': fin_trimestre
            }
        elif periode_type == 'annuel':
            debut_annee = aujourd_hui.replace(month=1, day=1)
            fin_annee = aujourd_hui.replace(month=12, day=31)
            return {
                'date_debut': debut_annee,
                'date_fin': fin_annee
            }
        else:
            return {
                'date_debut': aujourd_hui - timedelta(days=30),
                'date_fin': aujourd_hui
            }
    
    # === ACTIONS ===
    def action_regenerer_rapport(self):
        """Régénère le rapport avec les données actuelles"""
        self.ensure_one()
        
        # Forcer le recalcul de tous les champs computed
        self._compute_kpis_reception()
        self._compute_kpis_traitement()
        self._compute_kpis_numerisation()
        self._compute_kpis_indexation()
        self._compute_kpis_livraison()
        self._compute_taux_erreurs()
        self._compute_performance_agents()
        self._compute_tendances()
        
        self.message_post(
            body=_("Rapport régénéré avec les données actuelles"),
            subtype_xmlid='mail.mt_note'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rapport Régénéré'),
                'message': _('Le rapport a été mis à jour avec les dernières données'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_exporter_excel(self):
        """Exporte le rapport en Excel"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'archivage_collecteurs_complet.rapport_kpi_excel',
            'report_type': 'xlsx',
            'data': {'ids': [self.id]},
            'context': self.env.context,
        }
    
    def action_envoyer_par_email(self):
        """Envoie le rapport par email"""
        self.ensure_one()
        
        return {
            'name': _('Envoyer le Rapport par Email'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'context': {
                'default_model': 'reporting.kpi',
                'default_res_id': self.id,
                'default_subject': f'Rapport KPI - {self.nom_rapport}',
                'default_body': f'Veuillez trouver ci-joint le rapport KPI pour la période du {self.date_debut} au {self.date_fin}.',
            },
            'target': 'new',
        }
    
    # === MÉTHODES STATIQUES ===
    @api.model
    def generer_rapport_automatique(self, periode_type='mensuel'):
        """Génère automatiquement un rapport pour la période spécifiée"""
        dates = self._get_dates_periode(periode_type)
        
        nom_rapport = f"Rapport {periode_type.title()} - {dates['date_debut'].strftime('%B %Y')}"
        
        rapport = self.create({
            'nom_rapport': nom_rapport,
            'periode_type': periode_type,
            'date_debut': dates['date_debut'],
            'date_fin': dates['date_fin']
        })
        
        return rapport
    
    @api.model
    def get_dashboard_data(self):
        """Retourne les données pour le tableau de bord"""
        aujourd_hui = fields.Date.today()
        debut_mois = aujourd_hui.replace(day=1)
        
        # Données du mois en cours
        rapport_mois = self.search([
            ('periode_type', '=', 'mensuel'),
            ('date_debut', '=', debut_mois)
        ], limit=1)
        
        if not rapport_mois:
            rapport_mois = self.generer_rapport_automatique('mensuel')
        
        # Données de la semaine en cours
        debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        rapport_semaine = self.search([
            ('periode_type', '=', 'hebdomadaire'),
            ('date_debut', '=', debut_semaine)
        ], limit=1)
        
        if not rapport_semaine:
            rapport_semaine = self.generer_rapport_automatique('hebdomadaire')
        
        # Données du jour
        rapport_jour = self.search([
            ('periode_type', '=', 'quotidien'),
            ('date_debut', '=', aujourd_hui)
        ], limit=1)
        
        if not rapport_jour:
            rapport_jour = self.generer_rapport_automatique('quotidien')
        
        return {
            'mensuel': {
                'dossiers_receptionnes': rapport_mois.nb_dossiers_receptionnes,
                'dossiers_traites': rapport_mois.nb_dossiers_traites,
                'dossiers_numerises': rapport_mois.nb_dossiers_numerises,
                'pieces_indexees': rapport_mois.nb_pieces_indexees,
                'receptions_livrees': rapport_mois.nb_receptions_livrees,
                'taux_erreurs': rapport_mois.taux_erreurs,
                'evolution_reception': rapport_mois.evolution_reception,
                'evolution_traitement': rapport_mois.evolution_traitement,
                'evolution_numerisation': rapport_mois.evolution_numerisation,
            },
            'hebdomadaire': {
                'dossiers_receptionnes': rapport_semaine.nb_dossiers_receptionnes,
                'dossiers_traites': rapport_semaine.nb_dossiers_traites,
                'dossiers_numerises': rapport_semaine.nb_dossiers_numerises,
                'pieces_indexees': rapport_semaine.nb_pieces_indexees,
                'receptions_livrees': rapport_semaine.nb_receptions_livrees,
            },
            'quotidien': {
                'dossiers_receptionnes': rapport_jour.nb_dossiers_receptionnes,
                'dossiers_traites': rapport_jour.nb_dossiers_traites,
                'dossiers_numerises': rapport_jour.nb_dossiers_numerises,
                'pieces_indexees': rapport_jour.nb_pieces_indexees,
                'receptions_livrees': rapport_jour.nb_receptions_livrees,
            }
        }
    
    # === CONTRAINTES ===
    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for record in self:
            if record.date_debut > record.date_fin:
                raise ValidationError(_("La date de début doit être antérieure à la date de fin."))
    
    # === MÉTHODES D'AFFICHAGE ===
    def name_get(self):
        result = []
        for record in self:
            name = record.nom_rapport
            if record.periode_type:
                name += f" ({record.periode_type.title()})"
            if record.date_debut and record.date_fin:
                name += f" - {record.date_debut} au {record.date_fin}"
            result.append((record.id, name))
        return result

