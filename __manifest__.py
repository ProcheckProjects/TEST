# -*- coding: utf-8 -*-
{
    'name': 'Archivage Dossiers Collecteurs',
    'version': '16.0.1.0.0',
    'category': 'Operations/Inventory',
    'summary': 'Gestion complète de la chaîne de traitement des dossiers collecteurs',
    'description': """
Archivage Dossiers Collecteurs
===============================

Ce module implémente la chaîne complète de traitement des dossiers collecteurs pour CIH Bank :

Fonctionnalités principales :
-----------------------------
* Réception des dossiers avec bordereau de livraison
* Traitement physique avec calcul automatique des durées
* Transfert automatisé entre zones de stock
* Numérisation avec gestion des types de dossiers
* Indexation des documents avec métadonnées
* Livraison numérique automatisée vers CIH Bank
* Tableaux de bord et KPIs en temps réel
* Gestion des droits d'accès par rôle utilisateur

Workflow en 6 étapes :
---------------------
1. Réception (Archiviste)
2. Traitement Physique (Agent de traitement)
3. Transfert Numérisation (Gestionnaire de stock)
4. Numérisation (Opérateur de numérisation)
5. Indexation (Agent d'indexation)
6. Livraison Numérique (Archiviste)

KPIs et Reporting :
------------------
* Nombre de dossiers réceptionnés (quotidien/hebdomadaire/mensuel)
* Durée moyenne de traitement par agent
* Nombre de dossiers numérisés par jour
* Nombre de pièces indexées
* Taux d'écarts ou erreurs
* Nombre de réceptions livrées

Interfaces utilisateur :
-----------------------
* Interface de réception intuitive pour archivistes
* Interface de création et gestion des cartons
* Interfaces spécialisées par rôle utilisateur
* Tableaux de bord avec KPIs visuels
* Notifications automatiques entre étapes

Sécurité et Droits d'accès :
---------------------------
* Groupes de sécurité par rôle
* Accès restreint aux données selon le rôle
* Traçabilité complète des opérations
* Notifications automatiques entre étapes
    """,
    'author': 'Manus AI',
    'website': 'https://www.manus.ai',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'stock',
        'product',
        'web',
        'board'
    ],
    'data': [
        # Sécurité
        'security/archivage_collecteurs_security.xml',
        'security/ir.model.access.csv',
        
        # Données de base
        'data/stock_location_data.xml',
        'data/stock_picking_type_data.xml',
        'data/sequence_data.xml',
        
        # Actions

        
        # Vues principales
        'views/reception_dossier_views.xml',
        'views/dossier_collecteur_views.xml',
        'views/traitement_physique_views.xml',
        'views/carton_numerisation_views.xml',
        'views/numerisation_dossier_views.xml',
        'views/indexation_dossier_views.xml',
        'views/livraison_numerique_views.xml',
        'views/reporting_kpi_views.xml',
        'views/actions.xml',
        
        # Wizards
        'views/wizard_views.xml',
        
        # Menus (doit être en dernier)
        'views/menuitem.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 10,
    'images': ['static/description/banner.png'],
}

