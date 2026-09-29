-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ruan Pato

CREATE USER grafana_reader WITH PASSWORD 'local-readonly';
GRANT CONNECT ON DATABASE tracequota TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE tracequota IN SCHEMA public GRANT SELECT ON TABLES TO grafana_reader;
