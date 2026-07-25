-- Mock medical language tags (generated 2026-07-25)
-- Purpose: reproducibly seed the 50 local-demo language labels created for
-- medical venues. This file is deliberately placed under scripts rather than
-- init: its venue IDs are created by the source/ETL load, after MySQL init.
--
-- Safe to rerun: only fills NULL or empty language_tags. Existing labels are
-- never overwritten.
--
-- Apply after the venue ETL:
--   docker exec -i -e MYSQL_PWD=clearpath_app clearpath-mysql \
--     mysql -uclearpath_app -D clearpath < docker/mysql/scripts/seed_mock_medical_languages.sql

START TRANSACTION;

CREATE TEMPORARY TABLE mock_medical_language_tags (
  venue_id VARCHAR(36) PRIMARY KEY,
  language_tags JSON NOT NULL
);

INSERT INTO mock_medical_language_tags (venue_id, language_tags) VALUES
  ('032cf0db702d7ee481a14988ec5d85b8c833', JSON_ARRAY('de', 'zh', 'es')),
  ('0d936bf077d1346b5d9691750270f91fc00b', JSON_ARRAY('fr', 'zh', 'es')),
  ('2040082e8353dde4e50071833b750b17bcab', JSON_ARRAY('fr', 'zh', 'es')),
  ('20e7e792b619ad46d3619e1923c09e87e8b6', JSON_ARRAY('es')),
  ('2981288dadae76edde7a3395ae94f5c0c637', JSON_ARRAY('es')),
  ('2af98e0d16177e1632739739506fe2059735', JSON_ARRAY('zh')),
  ('2ec384877fbce3b8835a05ee50ef145fe994', JSON_ARRAY('de', 'zh', 'es')),
  ('3341456650817672253241f1979840a4e7fe', JSON_ARRAY('it', 'de')),
  ('34ef7bc7528c3b8a23023065aa925a1480b4', JSON_ARRAY('it', 'de')),
  ('3b0eadad8400c355acc1d00f9fc5fc9633d8', JSON_ARRAY('zh')),
  ('3b5f2fe81f410d21d89b89d0aabf1b3c0c74', JSON_ARRAY('zh')),
  ('443ad3496f431de9610368bf2c37bccdd186', JSON_ARRAY('zh')),
  ('444879d84524980d14e6f4ff56b29200e068', JSON_ARRAY('fr', 'zh', 'es')),
  ('44f528667fcab8e81de5e1306f515437cd22', JSON_ARRAY('fr', 'it')),
  ('44fdb5d352a7dc377a11d528a913d45e6328', JSON_ARRAY('it', 'de')),
  ('46bfe5c18bfdc906b2cd31163904ce9b5e35', JSON_ARRAY('fr', 'it')),
  ('4a59f71e60d030e399d55e0ac559523d9c7a', JSON_ARRAY('de', 'zh', 'es')),
  ('4b3f225e1b3d71c920cbceb28cc5ad55ad29', JSON_ARRAY('fr', 'it')),
  ('4b85884ce046ee65015a12c6744928e03ae8', JSON_ARRAY('fr', 'it')),
  ('4eeab245ae36f0ded3069c674ded44528cfb', JSON_ARRAY('zh')),
  ('628c405803ff9f4f86a6d9494bed2989a448', JSON_ARRAY('it', 'de')),
  ('633974e432d8131ed914157259745646f956', JSON_ARRAY('es')),
  ('64f085e5812e3769618e0c01eb9d7e49c600', JSON_ARRAY('zh')),
  ('67a88989363834acc61601b6d1871ca47916', JSON_ARRAY('es')),
  ('69c7b0b502ba66dd63ab76af4b0c74f5482f', JSON_ARRAY('es')),
  ('6afd8ff7794ffedd0db7b25f4b86f852299e', JSON_ARRAY('it', 'de')),
  ('759c17953ac6cdd9da306a0d210c7184c4c8', JSON_ARRAY('fr', 'it')),
  ('7beb7c16dc57c4c800af84d380aef1f335ef', JSON_ARRAY('fr', 'zh', 'es')),
  ('8114c9e61fb3a5664d3dd1bd3784e0c05180', JSON_ARRAY('it', 'de')),
  ('844ed37ab164b7d886b034e1abc0e7b30e96', JSON_ARRAY('es')),
  ('8e601550e36050a7f93e5a7d072c4320b48b', JSON_ARRAY('es')),
  ('9037cbdd4fc4e2a7f4b53e8b0139411fb204', JSON_ARRAY('fr', 'it')),
  ('947bd88c33f3f37291ac78192b5c38f573fe', JSON_ARRAY('it', 'de')),
  ('a660bc32a6bc88a6166c7f4923c561ed3f6e', JSON_ARRAY('zh')),
  ('b3cc71de0bcf61d81a4a9d0b205f25906b6a', JSON_ARRAY('fr', 'it')),
  ('b82de341bdb17200840c769a1ccf65b58bfd', JSON_ARRAY('fr', 'it')),
  ('bd975a5d488108329aa2f91b384261587035', JSON_ARRAY('fr', 'zh', 'es')),
  ('c3f2ca8333c425024d91d7bb854e0278665a', JSON_ARRAY('de', 'zh', 'es')),
  ('c8f43ce0fe06770d22bdb721ad2f4719d02c', JSON_ARRAY('fr', 'zh', 'es')),
  ('cd43d7fee5374a6763fd9999d90954f3fd44', JSON_ARRAY('de', 'zh', 'es')),
  ('da982494cbe4dfd1dadfff1f1c146f833f08', JSON_ARRAY('de', 'zh', 'es')),
  ('deff75653ca4a78051f2ff36f582b2bb5820', JSON_ARRAY('fr', 'it')),
  ('e4a206fb5c00cdadc7f3c52002f3ed6b3aa5', JSON_ARRAY('es')),
  ('e64be246dd29b78efdf3b1b34320b748c1f6', JSON_ARRAY('de', 'zh', 'es')),
  ('ea585f145c0af558b3ac3a6258e993fca8a2', JSON_ARRAY('fr', 'zh', 'es')),
  ('f11db355849c6583656cb1e6cb8f6b605e43', JSON_ARRAY('de', 'zh', 'es')),
  ('f24dde391d9e3c059834f06589a1137c960c', JSON_ARRAY('it', 'de')),
  ('f4bbe4fe91b093164786dd61f102f21000f9', JSON_ARRAY('zh')),
  ('f4df86ac19e99cdb47a6b359aa16fe14918a', JSON_ARRAY('fr', 'zh', 'es')),
  ('f65915d88909a8b328b89cd8e5383a91943a', JSON_ARRAY('de', 'zh', 'es'));

UPDATE venues AS v
JOIN mock_medical_language_tags AS mock ON mock.venue_id = v.venue_id
SET v.language_tags = mock.language_tags
WHERE v.venue_type IN ('healthcare', 'clinic', 'hospital', 'pharmacy', 'dentist', 'laboratory')
  AND (v.language_tags IS NULL OR JSON_LENGTH(v.language_tags) = 0);

-- Verification: this must return 50 after the source venue load.
SELECT
  COUNT(*) AS expected_mock_venue_count,
  SUM(v.language_tags = mock.language_tags) AS matching_language_tag_count
FROM mock_medical_language_tags AS mock
LEFT JOIN venues AS v ON v.venue_id = mock.venue_id;

COMMIT;

