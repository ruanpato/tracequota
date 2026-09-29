# GitHub Copilot CLI → TraceQuota

Status: **planned / experimental** adapter descriptor. No native Copilot export, official quota collector or subscription billing mapping has been verified or implemented in this release. A configured descriptor does not certify support. Consult [official Copilot documentation](https://docs.github.com/en/copilot) for your installed version; no exporter flags are invented here.

The extension path is an adapter that emits safe OTLP model/tool events to the existing Collector, with `tracequota.client.id=copilot_cli`, client version, surface, runtime and actual provider/model/billing platform. Mark integration type `tracequota_adapter` or `experimental`. Never infer provider from Copilot client identity. Missing provider/cache/usage semantics must stay unknown.

Implement and independently test the documented canonical contract before labeling live support. Avoid undocumented billing endpoints, credential reading, content capture or quota-consuming probes. Cross-platform adapters reuse the existing Compose stack and local OTLP HTTP/gRPC ports. See [pricing architecture](../pricing/architecture.md) for nullable quantities, attribution and provenance.
