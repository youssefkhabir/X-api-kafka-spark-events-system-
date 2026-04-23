# Rapport du projet : plateforme d'analyse temps reel avec Flask, Kafka, Spark et IA

## 1. Introduction

Ce projet presente une petite plateforme d'analyse de flux de messages en temps reel. L'objectif est de construire une chaine complete capable de :

- collecter des messages
- les publier dans Kafka
- les traiter en continu avec Spark Structured Streaming
- enrichir les donnees par analyse de sentiment
- exposer les resultats dans une interface web et une API documentee

Le systeme a ete pense comme une base simple, modulaire et demonstrable pour illustrer une architecture orientee evenements appliquee a l'analyse de contenu textuel.

## 2. Objectif du projet

L'objectif principal est de transformer un flux de messages bruts en informations exploitables quasi en temps reel.

Le projet cherche plus precisement a fournir :

- une ingestion de donnees souple
- un transport fiable des evenements via Kafka
- un traitement streaming avec Spark
- une analyse de sentiment simple et interpretable
- une extension vers l'intelligence artificielle via un modele supervise
- une visualisation claire pour la consultation et la demonstration

## 3. Vue d'ensemble de l'architecture

Le pipeline retenu est le suivant :

`Source de messages -> Flask -> Kafka raw_posts -> Spark Structured Streaming -> Kafka predictions -> Dashboard + API`

Cette architecture se compose de cinq blocs principaux :

1. une source de messages
2. une couche d'ingestion Flask
3. un bus d'evenements Kafka
4. une couche d'analyse Spark
5. une couche de consultation via dashboard et Swagger UI

## 4. Description des composants

### 4.1 Source de donnees

Le systeme prend en charge deux modes d'alimentation :

- un mode local base sur un fichier JSONL d'exemple
- un mode distant base sur l'API publique de Bluesky

Le mode local permet de tester et de presenter le projet sans dependre d'une API externe. Le mode distant permet de montrer une integration avec une source reelle.

### 4.2 Flask

Flask est utilise comme couche applicative centrale.

Ses responsabilites sont les suivantes :

- servir le dashboard principal
- exposer les endpoints HTTP
- publier des evenements dans Kafka
- fournir une specification OpenAPI
- servir l'interface Swagger UI

Le choix de Flask est adapte a un projet compact car il permet de garder une structure simple tout en offrant une base suffisante pour une API et une interface web.

### 4.3 Kafka

Kafka joue le role de colonne vertebrale de l'application.

Deux topics sont utilises :

- `raw_posts` pour les messages bruts
- `predictions` pour les messages enrichis apres traitement

Ce decouplage apporte plusieurs avantages :

- separation claire entre ingestion et analyse
- reutilisation possible des donnees brutes
- possibilite d'ajouter d'autres consommateurs plus tard
- meilleure lisibilite de l'architecture

### 4.4 Spark Structured Streaming

Spark consomme les messages depuis Kafka et applique le traitement en continu.

Les principales etapes sont :

- lecture du topic Kafka
- conversion du JSON en structure exploitable
- calcul du score de sentiment
- attribution d'un label
- extraction des hashtags
- agregations sur des fenetres temporelles
- republication des donnees enrichies dans Kafka

Spark a ete choisi pour sa capacite a traiter des flux de donnees de facon declarative et pour sa bonne integration avec Kafka.

### 4.5 Couche IA

Une extension IA a ete ajoutee sous forme d'un modele supervise simple.

Le pipeline de prediction utilise :

- une vectorisation TF-IDF
- un classifieur Logistic Regression

Ce modele reste volontairement leger. Le but n'est pas de construire un systeme de classification de production, mais d'ajouter une dimension predictive au projet et de comparer deux approches :

- une approche par regles lexicales
- une approche basee sur l'apprentissage automatique

## 5. Fonctionnement detaille du pipeline

Le pipeline complet peut etre decrit comme suit :

### Etape 1 : ingestion

Un message est recupere soit depuis le fichier local, soit depuis l'API publique de Bluesky. Flask convertit ensuite ce message dans un format JSON uniforme contenant les champs principaux :

- identifiant
- source
- texte
- langue
- auteur
- date de creation

### Etape 2 : publication dans Kafka

Le message est envoye dans le topic `raw_posts`.

Cette etape permet de rendre les donnees disponibles pour un ou plusieurs consommateurs independants.

### Etape 3 : traitement Spark

Spark lit le flux depuis Kafka puis applique plusieurs transformations :

- parsing du payload
- enrichissement du message
- calcul du score lexicographique
- extraction des hashtags
- prediction ML si le modele est disponible

### Etape 4 : production des resultats

Spark publie les messages enrichis dans le topic `predictions`.

En parallele, des sorties console sont produites pour montrer :

- le nombre de messages par sentiment
- la repartition des hashtags par fenetre temporelle

### Etape 5 : exposition des resultats

Le dashboard Flask lit les messages les plus recents dans Kafka et construit un resume :

- volume global
- ratios de sentiments
- balance positif / negatif
- hashtags dominants
- chronologie recente
- derniers evenements traites

## 6. Analyse de sentiment

### 6.1 Methode lexicale

La premiere methode utilise un petit lexique de mots positifs et negatifs.

Le principe est simple :

- chaque mot positif augmente le score
- chaque mot negatif diminue le score
- le signe final du score determine le label

Cette methode est utile pour plusieurs raisons :

- elle est rapide
- elle est interpretable
- elle est facile a expliquer
- elle fonctionne sans phase d'entrainement

### 6.2 Methode supervisee

La seconde methode repose sur un modele de classification entraine sur un petit jeu d'exemples.

Cette approche permet d'introduire une logique plus flexible que la simple recherche de mots-clés. Elle montre aussi comment un composant d'IA peut etre integre dans un pipeline streaming.

## 7. Dashboard et visualisation

Le dashboard a ete concu pour etre lisible, moderne et utile pendant une presentation.

Il affiche :

- les indicateurs principaux en haut de page
- un graphe simplifie du rythme des evenements
- une repartition visuelle des sentiments
- les hashtags les plus frequents
- les sources detectees
- la liste des derniers messages vus

Le dashboard interroge periodiquement l'endpoint `/api/dashboard/summary` afin d'actualiser les donnees automatiquement.

## 8. Documentation de l'API

L'application expose une documentation interactive via Swagger UI.

Cette partie est importante pour :

- comprendre rapidement les routes disponibles
- tester les endpoints sans outil externe
- presenter l'API de maniere claire

Les principales routes exposees sont :

- `GET /`
- `GET /health`
- `POST /publish/sample`
- `POST /publish/bluesky`
- `GET /api/openapi.json`
- `GET /api/docs`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/events`

## 9. Choix techniques et justification

Plusieurs choix ont ete faits pour conserver un bon equilibre entre simplicite et valeur demonstrative.

### Flask

Flask permet de centraliser la partie web et API avec peu de complexite.

### Kafka

Kafka est adapte des qu'il faut transporter des evenements de maniere decouplee et robuste.

### Spark Structured Streaming

Spark permet de traiter un flux continu avec une logique proche du traitement batch, tout en restant lisible.

### Mode local + mode distant

La coexistence d'un mode local et d'un mode distant rend le projet plus robuste et plus facile a montrer dans differents contextes.

### IA legere

Un modele simple a ete prefere a une solution lourde afin de rester coherent avec la taille du projet et la facilite d'explication.

## 10. Limites du projet

Le projet reste volontairement compact. Il presente donc certaines limites :

- le modele ML repose sur un tres petit jeu d'apprentissage
- le dashboard lit Kafka directement, sans couche de stockage historique
- la disponibilite de l'API publique Bluesky peut varier selon les limites de service
- la visualisation reste simple et cible surtout la demonstration

Ces limites sont acceptees car elles permettent de garder un systeme lisible et facile a faire evoluer.

## 11. Pistes d'amelioration

Plusieurs evolutions sont possibles :

- brancher une base de donnees pour stocker l'historique
- utiliser un vrai dataset annote pour ameliorer le modele ML
- ajouter des alertes sur pics de traffic ou de sentiment negatif
- produire des graphiques plus avances
- conteneuriser toute l'architecture avec Docker Compose
- ajouter une authentification pour les routes sensibles

## 12. Conclusion

Le projet realise constitue une plateforme complete d'analyse de messages en temps reel.

Il montre comment assembler plusieurs briques complementaires :

- Flask pour l'exposition web et API
- Kafka pour le transport d'evenements
- Spark pour le traitement streaming
- une logique d'analyse de sentiment
- une couche de visualisation et de documentation

Le resultat est une architecture claire, modulaire et evolutive, suffisamment simple pour etre comprise rapidement, mais assez riche pour illustrer une vraie chaine de traitement orientee evenements avec une composante IA.
