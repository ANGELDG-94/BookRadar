-- MySQL dump 10.13  Distrib 8.0.38, for Win64 (x86_64)
--
-- Host: localhost    Database: bookradar
-- ------------------------------------------------------
-- Server version	9.5.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'fa56b6ba-db31-11f0-96a0-0a0027000008:1-76';

--
-- Table structure for table `generos`
--

DROP TABLE IF EXISTS `generos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `generos` (
  `id_genero` int NOT NULL AUTO_INCREMENT,
  `nombre_genero` varchar(50) NOT NULL,
  PRIMARY KEY (`id_genero`),
  UNIQUE KEY `nombre_genero_UNIQUE` (`nombre_genero`)
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Catálogo maestro de géneros literarios disponibles en la plataforma';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `generos`
--

LOCK TABLES `generos` WRITE;
/*!40000 ALTER TABLE `generos` DISABLE KEYS */;
INSERT INTO `generos` VALUES (13,'Autoayuda'),(10,'Aventura'),(7,'Biografía'),(2,'Ciencia Ficción'),(14,'Cómic/Manga'),(11,'Ensayo'),(3,'Fantasía'),(1,'Ficción'),(6,'Histórica'),(5,'Misterio'),(12,'Poesía'),(9,'Romance'),(8,'Terror'),(4,'Thriller');
/*!40000 ALTER TABLE `generos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lecturas`
--

DROP TABLE IF EXISTS `lecturas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lecturas` (
  `id_lecturas` int NOT NULL AUTO_INCREMENT,
  `id_usuario` int NOT NULL,
  `estado` enum('QUIERO_LEER','LEIDO','DESCARTADO') NOT NULL,
  `puntuación` int DEFAULT NULL,
  `comentario` longtext,
  PRIMARY KEY (`id_lecturas`),
  KEY `fk_lectura_usuario_idx` (`id_usuario`),
  CONSTRAINT `fk_lectura_libro` FOREIGN KEY (`id_lecturas`) REFERENCES `libros` (`id_libros`),
  CONSTRAINT `fk_lectura_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuarios`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lecturas`
--

LOCK TABLES `lecturas` WRITE;
/*!40000 ALTER TABLE `lecturas` DISABLE KEYS */;
/*!40000 ALTER TABLE `lecturas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `libros`
--

DROP TABLE IF EXISTS `libros`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `libros` (
  `id_libros` int NOT NULL,
  `titulo` varchar(300) NOT NULL,
  `autor` varchar(300) NOT NULL,
  `fecha_publicacion` varchar(20) DEFAULT NULL,
  `portada` varchar(500) DEFAULT NULL,
  `sinopsis` longtext,
  PRIMARY KEY (`id_libros`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='informacion de libro';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `libros`
--

LOCK TABLES `libros` WRITE;
/*!40000 ALTER TABLE `libros` DISABLE KEYS */;
/*!40000 ALTER TABLE `libros` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `preferencias_usuarios`
--

DROP TABLE IF EXISTS `preferencias_usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `preferencias_usuarios` (
  `id_usuario` int NOT NULL,
  `id_genero` int NOT NULL,
  PRIMARY KEY (`id_usuario`,`id_genero`),
  KEY `fk_preferencias_genero_idx` (`id_genero`),
  CONSTRAINT `fk_preferencias_genero` FOREIGN KEY (`id_genero`) REFERENCES `generos` (`id_genero`),
  CONSTRAINT `fk_preferencias_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuarios`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `preferencias_usuarios`
--

LOCK TABLES `preferencias_usuarios` WRITE;
/*!40000 ALTER TABLE `preferencias_usuarios` DISABLE KEYS */;
/*!40000 ALTER TABLE `preferencias_usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id_usuarios` int NOT NULL AUTO_INCREMENT,
  `nombre_usuario` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `contraseña` varchar(300) NOT NULL,
  `fecha_registro` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_usuarios`),
  UNIQUE KEY `nombre_usuario_UNIQUE` (`nombre_usuario`),
  UNIQUE KEY `email_UNIQUE` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Datos de usuario';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-17 13:04:24
