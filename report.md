# Rapport du projet : Pipeline temps reel avec Flask, Kafka, Spark et analyse de sentiment

## 1. Contexte

Ce projet a ete realise pour repondre au TP sur l'analyse de messages de reseaux sociaux en temps reel. L'objectif principal est de construire une chaine de traitement capable de collecter des messages, de les envoyer dans Kafka, de les analyser avec Spark Structured Streaming, puis d'exposer les resultats dans une interface web exploitable pendant une presentation.

Le sujet du TP met l'accent sur plusieurs notions importantes :

- le stream processing
- l'ingestion de donnees temps reel
- l'utilisation de Kafka comme systeme de transport d'evenements
- l'utilisation de Spark Structured Streaming pour l'analyse continue
- la comparaison entre une methode simple de type lexique et une approche d'apprentissage automatique

## 2. Objectif du systeme realise

Le systeme final a ete pense comme une petite plateforme de supervision d'evenements sociaux autour d'un sujet donne.

Le pipeline retenu est le suivant :

`X API ou jeu de donnees local -> Flask -> Kafka -> Spark Structured Streaming -> topic predictions -> Dashboard + Swagger UI`

Cette architecture permet de montrer clairement les differentes etapes du traitement temps reel :

1. collecte ou simulation des messages
2. publication dans Kafka
3. traitement en continu dans Spark
4. calcul des indicateurs de sentiment et des hashtags
5. exposition des resultats dans une API et un tableau de bord

## 3. Choix d'architecture

### 3.1 Flask

Flask joue ici le role de couche d'orchestration et de presentation.

Il permet :

- d'exposer des endpoints HTTP simples pour lancer l'envoi de donnees
- de centraliser la configuration du projet
- de fournir une page dashboard pour la demonstration
- de fournir une documentation interactive avec Swagger UI

Le choix de Flask est pertinent pour un mini projet car il est leger, lisible et rapide a mettre en place.

### 3.2 Kafka

Kafka est utilise comme bus d'evenements. Il se situe entre la collecte et l'analyse.

Deux topics sont utilises :

- `raw_posts` : messages bruts envoyes depuis Flask
- `predictions` : messages enrichis par Spark apres analyse

Ce decouplage est important car il montre bien la separation entre :

- l'etape d'ingestion
- l'etape de traitement
- l'etape d'exploitation des resultats

### 3.3 Spark Structured Streaming

Spark consomme les messages depuis Kafka, applique un schema, enrichit les donnees et calcule des indicateurs.

Les traitements mis en place sont :

- lecture du flux Kafka
- parsing JSON
- calcul du score lexicographique
- affectation d'un label de sentiment
- extraction des hashtags
- agregations par fenetre temporelle
- republication des donnees enrichies dans un topic Kafka

Spark est ici le moteur central d'analyse temps reel.

### 3.4 Couche IA

L'IA a ete introduite sous la forme d'un modele supervise simple.

Le choix retenu est :

- vectorisation TF-IDF
- classification par Logistic Regression

Ce choix est volontairement pragmatique :

- facile a expliquer en classe
- simple a entrainer
- rapide a executer
- pertinent pour comparer avec la methode lexicale

L'application donne donc deux niveaux d'analyse :

- une baseline lexicale
- une prediction ML optionnelle

## 4. Approche de realisation

Le travail a ete organise par etapes afin de construire un systeme demonstrable le plus vite possible.

### Etape 1 : lecture du besoin

Le PDF du TP a ete lu pour identifier les exigences pedagogiques :

- API X/Twitter
- Kafka
- Spark Streaming
- analyse de sentiment
- ouverture vers une approche ML

### Etape 2 : definition d'un mode realiste

Une contrainte pratique a ete prise en compte : l'acces a l'API X peut etre limite selon le niveau de compte. Pour eviter qu'un probleme d'acces bloque la demonstration, deux modes ont ete prevus :

- un mode `reel` avec appel a l'API X
- un mode `demo-safe` base sur un fichier local JSONL rejoue dans Kafka

Ce choix permet de garantir que le pipeline fonctionne meme sans acces complet a l'API X.

### Etape 3 : mise en place du producteur

Un producteur Kafka a ete implemente dans Flask afin de publier des evenements JSON dans le topic `raw_posts`.

Deux routes d'alimentation ont ete ajoutees :

- publication depuis un fichier local d'exemple
- publication depuis l'API X via un bearer token

### Etape 4 : mise en place du consumer Spark

Un script Spark Structured Streaming a ete developpe pour :

- lire les messages depuis Kafka
- extraire les champs utiles
- enrichir chaque message
- calculer les agregats de sentiment et hashtags
- republier les resultats dans `predictions`

### Etape 5 : ajout du modele ML

Un petit script d'entrainement a ete ajoute pour produire un modele de classification. Ce modele est charge automatiquement par Spark s'il est disponible.

Ainsi, le projet peut fonctionner :

- avec uniquement l'approche lexicale
- ou avec l'approche lexicale + ML

### Etape 6 : ajout de la couche presentation

Deux briques ont ete ajoutees pour la presentation finale :

- Swagger UI pour tester facilement les endpoints
- un dashboard web pour suivre les indicateurs de facon visuelle

## 5. Composants implementes

### 5.1 API Flask

Les principales routes disponibles sont :

- `GET /` : dashboard principal
- `GET /health` : etat de l'application
- `POST /publish/sample` : envoi de donnees d'exemple vers Kafka
- `POST /publish/x` : envoi de donnees depuis X vers Kafka
- `GET /api/openapi.json` : specification OpenAPI
- `GET /api/docs` : interface Swagger UI
- `GET /api/dashboard/summary` : resume dashboard
- `GET /api/dashboard/events` : derniers evenements visibles

### 5.2 Analyse lexicale

Une liste de mots positifs et negatifs est utilisee pour calculer un score simple :

- score > 0 : positif
- score < 0 : negatif
- score = 0 : neutre

Cette methode est simple, interpretable, et correspond directement a l'attendu du TP.

### 5.3 Modele ML

Le modele supervise repose sur un petit jeu d'exemples d'entrainement integre au projet. L'idee n'est pas de viser la meilleure performance academique, mais de montrer l'integration d'une couche d'intelligence artificielle dans un pipeline temps reel.

### 5.4 Dashboard

Le dashboard a ete pense pour la soutenance. Il affiche :

- le volume total d'evenements
- le ratio de sentiments positifs et negatifs
- la balance de sentiment
- le rythme d'arrivee des messages
- les hashtags dominants
- les derniers evenements traites

Le dashboard lit en priorite les donnees du topic `predictions`. Si celui-ci est vide, il bascule en lecture sur `raw_posts` pour conserver un affichage fonctionnel.

### 5.5 Swagger UI

Swagger UI permet de tester rapidement l'API sans Postman ni outil externe. L'integration repose sur une page HTML servant l'interface Swagger et pointant vers la specification OpenAPI locale.

Cette partie est utile pour :

- verifier les endpoints
- montrer la structure de l'API
- faciliter les demonstrations en classe

## 6. Pipeline fonctionnel

Le fonctionnement global du systeme est le suivant :

1. L'utilisateur lance Zookeeper et Kafka localement.
2. L'utilisateur lance l'application Flask.
3. L'utilisateur lance le script Spark Structured Streaming.
4. Les messages sont publies vers `raw_posts`.
5. Spark consomme le flux, calcule les indicateurs, puis ecrit dans `predictions`.
6. Le dashboard lit les resultats et les affiche en temps reel.
7. Swagger UI permet de tester les routes a tout moment.

## 7. Apport de l'intelligence artificielle

L'ajout de l'IA dans ce projet se manifeste par l'integration d'un modele de classification supervisee.

L'interet pedagogique est double :

- montrer qu'un pipeline streaming peut integrer un composant ML
- comparer une methode simple basee sur un lexique avec une methode predictive

Cette comparaison permet d'expliquer plusieurs notions :

- la simplicite et la rapidite d'une methode par regles
- la flexibilite d'un modele appris
- les limites d'un jeu d'entrainement trop petit

## 8. Limites actuelles

Le projet est volontairement compact. Il existe donc plusieurs limites :

- le modele ML est entraine sur un tres petit jeu de donnees
- le dashboard lit Kafka a la demande au lieu d'utiliser un stockage specialise
- l'acces reel a l'API X depend du niveau d'acces developpeur
- il n'y a pas encore de base de donnees historique

Ces limites sont acceptees dans le cadre d'un mini projet pedagogique car elles permettent de privilegier la clarte de l'architecture.

## 9. Ameliorations possibles

Plusieurs extensions peuvent etre ajoutees ensuite :

- stockage des resultats dans PostgreSQL ou Elasticsearch
- ajout de graphiques historiques plus pousses
- enrichissement du modele ML avec un vrai dataset annote
- systeme d'alertes sur pics d'activite
- deploiement avec Docker Compose
- authentification des endpoints d'administration

## 10. Conclusion

Le projet realise repond aux objectifs essentiels du TP :

- ingestion d'un flux de messages
- publication dans Kafka
- traitement temps reel avec Spark Structured Streaming
- analyse de sentiment
- ouverture vers une approche IA
- presentation via dashboard et documentation interactive

L'approche retenue privilegie la robustesse de demonstration, la lisibilite du pipeline et la clarte pedagogique. Le resultat est un mini systeme coherent, presentable en classe, et suffisamment modulaire pour etre enrichi ensuite.
