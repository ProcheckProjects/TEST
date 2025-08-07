# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    # === INFORMATIONS SPÉCIFIQUES ARCHIVAGE ===
    matricule_agent = fields.Char(
        string='Matricule Agent',
        help="Matricule unique de l'agent"
    )
    
    specialite_archivage = fields.Selection([
        ('reception', 'Réception'),
        ('traitement', 'Traitement Physique'),
        ('stock', 'Gestion de Stock'),
        ('numerisation', 'Numérisation'),
        ('indexation', 'Indexation'),
        ('livraison', 'Livraison'),
        ('supervision', 'Supervision')
    ], string='Spécialité Archivage', help="Spécialité de l'agent dans le processus d'archivage")
    
    niveau_experience = fields.Selection([
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('experimente', 'Expérimenté'),
        ('expert', 'Expert')
    ], string='Niveau d\'Expérience', default='debutant', help="Niveau d'expérience de l'agent")
    
    date_formation = fields.Date(
        string='Date de Formation',
        help="Date de la dernière formation"
    )
    
    certifie = fields.Boolean(
        string='Certifié',
        default=False,
        help="Indique si l'agent est certifié pour son poste"
    )
    
    # === STATISTIQUES DE PERFORMANCE ===
    nb_dossiers_traites_total = fields.Integer(
        string='Dossiers Traités (Total)',
        compute='_compute_statistiques_performance',
        help="Nombre total de dossiers traités par l'agent"
    )
    
    nb_dossiers_traites_mois = fields.Integer(
        string='Dossiers Traités (Ce Mois)',
        compute='_compute_statistiques_performance',
        help="Nombre de dossiers traités ce mois"
    )
    
    duree_moyenne_traitement = fields.Float(
        string='Durée Moyenne Traitement (min)',
        compute='_compute_statistiques_performance',
        help="Durée moyenne de traitement par dossier"
    )
    
    vitesse_moyenne_travail = fields.Float(
        string='Vitesse Moyenne (pièces/min)',
        compute='_compute_statistiques_performance',
        help="Vitesse moyenne de travail"
    )
    
    taux_erreurs_agent = fields.Float(
        string='Taux d\'Erreurs (%)',
        compute='_compute_statistiques_performance',
        help="Taux d'erreurs de l'agent"
    )
    
    # === PLANNING ET DISPONIBILITÉ ===
    horaire_debut = fields.Float(
        string='Heure de Début',
        default=8.0,
        help="Heure de début de travail (format 24h)"
    )
    
    horaire_fin = fields.Float(
        string='Heure de Fin',
        default=17.0,
        help="Heure de fin de travail (format 24h)"
    )
    
    jours_travail = fields.Selection([
        ('lundi_vendredi', 'Lundi à Vendredi'),
        ('lundi_samedi', 'Lundi à Samedi'),
        ('personnalise', 'Personnalisé')
    ], string='Jours de Travail', default='lundi_vendredi', help="Jours de travail de l'agent")
    
    disponible = fields.Boolean(
        string='Disponible',
        default=True,
        help="Indique si l'agent est actuellement disponible"
    )
    
    en_conge = fields.Boolean(
        string='En Congé',
        default=False,
        help="Indique si l'agent est en congé"
    )
    
    date_debut_conge = fields.Date(
        string='Début Congé',
        help="Date de début du congé"
    )
    
    date_fin_conge = fields.Date(
        string='Fin Congé',
        help="Date de fin du congé"
    )
    
    # === OBJECTIFS ET QUOTAS ===
    objectif_quotidien = fields.Integer(
        string='Objectif Quotidien',
        help="Objectif quotidien de dossiers/pièces à traiter"
    )
    
    objectif_mensuel = fields.Integer(
        string='Objectif Mensuel',
        help="Objectif mensuel de dossiers/pièces à traiter"
    )
    
    quota_atteint_mois = fields.Boolean(
        string='Quota Atteint (Mois)',
        compute='_compute_quota_atteint',
        help="Indique si le quota mensuel est atteint"
    )
    
    pourcentage_objectif = fields.Float(
        string='% Objectif Atteint',
        compute='_compute_quota_atteint',
        help="Pourcentage de l'objectif mensuel atteint"
    )
    
    # === RELATIONS AVEC LES PROCESSUS ===
    reception_ids = fields.One2many(
        'reception.dossier',
        'archiviste_id',
        string='Réceptions',
        help="Réceptions gérées par cet archiviste"
    )
    
    traitement_ids = fields.One2many(
        'traitement.physique',
        'agent_id',
        string='Traitements',
        help="Traitements effectués par cet agent"
    )
    
    numerisation_ids = fields.One2many(
        'numerisation.dossier',
        'operateur_id',
        string='Numérisations',
        help="Numérisations effectuées par cet opérateur"
    )
    
    indexation_ids = fields.One2many(
        'indexation.dossier',
        'agent_id',
        string='Indexations',
        help="Indexations effectuées par cet agent"
    )
    
    livraison_ids = fields.One2many(
        'livraison.numerique',
        'archiviste_id',
        string='Livraisons',
        help="Livraisons gérées par cet archiviste"
    )
    
    carton_ids = fields.One2many(
        'carton.numerisation',
        'operateur_id',
        string='Cartons',
        help="Cartons gérés par cet opérateur"
    )
    
    # === NOTIFICATIONS ET ALERTES ===
    recevoir_notifications = fields.Boolean(
        string='Recevoir Notifications',
        default=True,
        help="Recevoir les notifications du workflow"
    )
    
    notification_email = fields.Boolean(
        string='Notifications par Email',
        default=True,
        help="Recevoir les notifications par email"
    )
    
    notification_interne = fields.Boolean(
        string='Notifications Internes',
        default=True,
        help="Recevoir les notifications internes Odoo"
    )
    
    # === MÉTHODES DE CALCUL ===
    @api.depends('traitement_ids', 'numerisation_ids', 'indexation_ids')
    def _compute_statistiques_performance(self):
        for user in self:
            # Calculer selon la spécialité de l'agent
            if user.specialite_archivage == 'traitement':
                user._compute_stats_traitement()
            elif user.specialite_archivage == 'numerisation':
                user._compute_stats_numerisation()
            elif user.specialite_archivage == 'indexation':
                user._compute_stats_indexation()
            else:
                # Valeurs par défaut
                user.nb_dossiers_traites_total = 0
                user.nb_dossiers_traites_mois = 0
                user.duree_moyenne_traitement = 0
                user.vitesse_moyenne_travail = 0
                user.taux_erreurs_agent = 0
    
    def _compute_stats_traitement(self):
        """Calcule les statistiques pour les agents de traitement"""
        self.ensure_one()
        
        # Total des traitements validés
        traitements_valides = self.traitement_ids.filtered(lambda t: t.state == 'valide')
        self.nb_dossiers_traites_total = len(traitements_valides)
        
        # Traitements du mois en cours
        debut_mois = fields.Date.today().replace(day=1)
        traitements_mois = traitements_valides.filtered(
            lambda t: t.heure_debut and t.heure_debut.date() >= debut_mois
        )
        self.nb_dossiers_traites_mois = len(traitements_mois)
        
        # Durée moyenne
        if traitements_valides:
            durees = traitements_valides.mapped('duree_effective')
            self.duree_moyenne_traitement = sum(durees) / len(durees) if durees else 0
            
            # Vitesse moyenne (pièces par minute)
            pieces_totales = sum(traitements_valides.mapped('nombre_pieces_traitees'))
            duree_totale = sum(durees)
            self.vitesse_moyenne_travail = pieces_totales / duree_totale if duree_totale > 0 else 0
        else:
            self.duree_moyenne_traitement = 0
            self.vitesse_moyenne_travail = 0
        
        # Taux d'erreurs
        traitements_erreur = self.traitement_ids.filtered(lambda t: t.state == 'erreur')
        total_traitements = len(self.traitement_ids)
        self.taux_erreurs_agent = (len(traitements_erreur) / total_traitements * 100) if total_traitements > 0 else 0
    
    def _compute_stats_numerisation(self):
        """Calcule les statistiques pour les opérateurs de numérisation"""
        self.ensure_one()
        
        # Total des numérisations validées
        numerisations_valides = self.numerisation_ids.filtered(lambda n: n.state == 'valide')
        self.nb_dossiers_traites_total = len(numerisations_valides)
        
        # Numérisations du mois en cours
        debut_mois = fields.Date.today().replace(day=1)
        numerisations_mois = numerisations_valides.filtered(
            lambda n: n.heure_debut and n.heure_debut.date() >= debut_mois
        )
        self.nb_dossiers_traites_mois = len(numerisations_mois)
        
        # Durée moyenne et vitesse
        if numerisations_valides:
            durees = numerisations_valides.mapped('duree_effective')
            self.duree_moyenne_traitement = sum(durees) / len(durees) if durees else 0
            
            vitesses = numerisations_valides.mapped('vitesse_numerisation')
            self.vitesse_moyenne_travail = sum(vitesses) / len(vitesses) if vitesses else 0
        else:
            self.duree_moyenne_traitement = 0
            self.vitesse_moyenne_travail = 0
        
        # Taux d'erreurs
        numerisations_erreur = self.numerisation_ids.filtered(lambda n: n.state == 'erreur')
        total_numerisations = len(self.numerisation_ids)
        self.taux_erreurs_agent = (len(numerisations_erreur) / total_numerisations * 100) if total_numerisations > 0 else 0
    
    def _compute_stats_indexation(self):
        """Calcule les statistiques pour les agents d'indexation"""
        self.ensure_one()
        
        # Total des indexations validées
        indexations_valides = self.indexation_ids.filtered(lambda i: i.state == 'valide')
        self.nb_dossiers_traites_total = len(indexations_valides)
        
        # Indexations du mois en cours
        debut_mois = fields.Date.today().replace(day=1)
        indexations_mois = indexations_valides.filtered(
            lambda i: i.heure_debut and i.heure_debut.date() >= debut_mois
        )
        self.nb_dossiers_traites_mois = len(indexations_mois)
        
        # Durée moyenne et vitesse
        if indexations_valides:
            durees = indexations_valides.mapped('duree_effective')
            self.duree_moyenne_traitement = sum(durees) / len(durees) if durees else 0
            
            vitesses = indexations_valides.mapped('vitesse_indexation')
            self.vitesse_moyenne_travail = sum(vitesses) / len(vitesses) if vitesses else 0
        else:
            self.duree_moyenne_traitement = 0
            self.vitesse_moyenne_travail = 0
        
        # Taux d'erreurs
        indexations_erreur = self.indexation_ids.filtered(lambda i: i.state == 'erreur')
        total_indexations = len(self.indexation_ids)
        self.taux_erreurs_agent = (len(indexations_erreur) / total_indexations * 100) if total_indexations > 0 else 0
    
    @api.depends('nb_dossiers_traites_mois', 'objectif_mensuel')
    def _compute_quota_atteint(self):
        for user in self:
            if user.objectif_mensuel > 0:
                user.pourcentage_objectif = (user.nb_dossiers_traites_mois / user.objectif_mensuel) * 100
                user.quota_atteint_mois = user.pourcentage_objectif >= 100
            else:
                user.pourcentage_objectif = 0
                user.quota_atteint_mois = False
    
    # === MÉTHODES D'ACTION ===
    def action_voir_performance(self):
        """Ouvre la vue détaillée des performances de l'agent"""
        self.ensure_one()
        
        if self.specialite_archivage == 'traitement':
            return {
                'name': _('Performances Traitement - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'traitement.physique',
                'view_mode': 'tree,form,graph,pivot',
                'domain': [('agent_id', '=', self.id)],
                'context': {'search_default_agent_id': self.id},
                'target': 'current',
            }
        elif self.specialite_archivage == 'numerisation':
            return {
                'name': _('Performances Numérisation - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'numerisation.dossier',
                'view_mode': 'tree,form,graph,pivot',
                'domain': [('operateur_id', '=', self.id)],
                'context': {'search_default_operateur_id': self.id},
                'target': 'current',
            }
        elif self.specialite_archivage == 'indexation':
            return {
                'name': _('Performances Indexation - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'indexation.dossier',
                'view_mode': 'tree,form,graph,pivot',
                'domain': [('agent_id', '=', self.id)],
                'context': {'search_default_agent_id': self.id},
                'target': 'current',
            }
        else:
            return {
                'name': _('Tableau de Bord - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'reporting.kpi',
                'view_mode': 'tree,form',
                'target': 'current',
            }
    
    def action_definir_conge(self):
        """Définit une période de congé pour l'agent"""
        self.ensure_one()
        
        return {
            'name': _('Définir Congé - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agent.conge.wizard',
            'view_mode': 'form',
            'context': {
                'default_agent_id': self.id,
            },
            'target': 'new',
        }
    
    def action_modifier_objectifs(self):
        """Modifie les objectifs de l'agent"""
        self.ensure_one()
        
        return {
            'name': _('Modifier Objectifs - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agent.objectifs.wizard',
            'view_mode': 'form',
            'context': {
                'default_agent_id': self.id,
                'default_objectif_quotidien': self.objectif_quotidien,
                'default_objectif_mensuel': self.objectif_mensuel,
            },
            'target': 'new',
        }
    
    def action_generer_rapport_agent(self):
        """Génère un rapport de performance pour l'agent"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'archivage_collecteurs_complet.rapport_performance_agent',
            'report_type': 'qweb-pdf',
            'data': {'agent_id': self.id},
            'context': self.env.context,
        }
    
    # === MÉTHODES UTILITAIRES ===
    def is_available_now(self):
        """Vérifie si l'agent est disponible maintenant"""
        self.ensure_one()
        
        if not self.disponible or self.en_conge:
            return False
        
        # Vérifier les congés
        if self.date_debut_conge and self.date_fin_conge:
            aujourd_hui = fields.Date.today()
            if self.date_debut_conge <= aujourd_hui <= self.date_fin_conge:
                return False
        
        # Vérifier les horaires de travail
        maintenant = datetime.now()
        heure_actuelle = maintenant.hour + maintenant.minute / 60.0
        
        if not (self.horaire_debut <= heure_actuelle <= self.horaire_fin):
            return False
        
        # Vérifier les jours de travail
        jour_semaine = maintenant.weekday()  # 0 = Lundi, 6 = Dimanche
        
        if self.jours_travail == 'lundi_vendredi' and jour_semaine > 4:
            return False
        elif self.jours_travail == 'lundi_samedi' and jour_semaine > 5:
            return False
        
        return True
    
    def get_workload_today(self):
        """Retourne la charge de travail actuelle de l'agent"""
        self.ensure_one()
        
        aujourd_hui = fields.Date.today()
        
        if self.specialite_archivage == 'traitement':
            return len(self.traitement_ids.filtered(
                lambda t: t.heure_debut and t.heure_debut.date() == aujourd_hui and t.state == 'en_cours'
            ))
        elif self.specialite_archivage == 'numerisation':
            return len(self.numerisation_ids.filtered(
                lambda n: n.heure_debut and n.heure_debut.date() == aujourd_hui and n.state == 'en_cours'
            ))
        elif self.specialite_archivage == 'indexation':
            return len(self.indexation_ids.filtered(
                lambda i: i.heure_debut and i.heure_debut.date() == aujourd_hui and i.state == 'en_cours'
            ))
        else:
            return 0
    
    @api.model
    def get_agents_disponibles(self, specialite=None):
        """Retourne la liste des agents disponibles pour une spécialité donnée"""
        domain = [('disponible', '=', True), ('en_conge', '=', False)]
        
        if specialite:
            domain.append(('specialite_archivage', '=', specialite))
        
        agents = self.search(domain)
        return agents.filtered(lambda a: a.is_available_now())
    
    @api.model
    def get_agent_moins_charge(self, specialite):
        """Retourne l'agent le moins chargé pour une spécialité donnée"""
        agents_disponibles = self.get_agents_disponibles(specialite)
        
        if not agents_disponibles:
            return None
        
        # Trier par charge de travail croissante
        agents_tries = sorted(agents_disponibles, key=lambda a: a.get_workload_today())
        return agents_tries[0] if agents_tries else None
    
    # === CONTRAINTES ===
    @api.constrains('horaire_debut', 'horaire_fin')
    def _check_horaires(self):
        for user in self:
            if user.horaire_debut >= user.horaire_fin:
                raise ValidationError(_("L'heure de début doit être antérieure à l'heure de fin."))
            if user.horaire_debut < 0 or user.horaire_fin > 24:
                raise ValidationError(_("Les horaires doivent être entre 0 et 24 heures."))
    
    @api.constrains('date_debut_conge', 'date_fin_conge')
    def _check_dates_conge(self):
        for user in self:
            if user.date_debut_conge and user.date_fin_conge:
                if user.date_debut_conge > user.date_fin_conge:
                    raise ValidationError(_("La date de début de congé doit être antérieure à la date de fin."))
    
    @api.constrains('objectif_quotidien', 'objectif_mensuel')
    def _check_objectifs(self):
        for user in self:
            if user.objectif_quotidien < 0 or user.objectif_mensuel < 0:
                raise ValidationError(_("Les objectifs ne peuvent pas être négatifs."))
    
    # === MÉTHODES AUTOMATIQUES ===
    @api.model
    def cron_update_conges(self):
        """Cron pour mettre à jour automatiquement les statuts de congé"""
        aujourd_hui = fields.Date.today()
        
        # Mettre en congé les agents dont la période de congé commence
        agents_debut_conge = self.search([
            ('date_debut_conge', '=', aujourd_hui),
            ('en_conge', '=', False)
        ])
        agents_debut_conge.write({'en_conge': True})
        
        # Sortir de congé les agents dont la période se termine
        agents_fin_conge = self.search([
            ('date_fin_conge', '=', aujourd_hui),
            ('en_conge', '=', True)
        ])
        agents_fin_conge.write({'en_conge': False})
    
    @api.model
    def cron_check_objectifs(self):
        """Cron pour vérifier l'atteinte des objectifs et envoyer des alertes"""
        debut_mois = fields.Date.today().replace(day=1)
        
        # Agents n'ayant pas atteint leurs objectifs à mi-mois
        if fields.Date.today().day == 15:
            agents_retard = self.search([
                ('objectif_mensuel', '>', 0),
                ('quota_atteint_mois', '=', False),
                ('pourcentage_objectif', '<', 50)  # Moins de 50% à mi-mois
            ])
            
            for agent in agents_retard:
                agent.message_post(
                    body=_("Alerte : Objectif mensuel en retard (%d%% atteint)") % agent.pourcentage_objectif,
                    subtype_xmlid='mail.mt_comment'
                )

