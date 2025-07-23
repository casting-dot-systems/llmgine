# LLMgine Documentation

## Project Documentation

- [Product Requirements Document (PRD)](./prd.md) - Original project requirements
- [Project Brief](./brief.md) - High-level project overview
- [Brownfield Enhancement PRD](./brownfield-prd/index.md) - Enhancement plans for production readiness

## Development Resources

### Brownfield Enhancement Structure
- [Project Analysis & Context](./brownfield-prd/intro-project-analysis-and-context.md)
- [Requirements](./brownfield-prd/requirements.md)
- [Technical Constraints](./brownfield-prd/technical-constraints-and-integration-requirements.md)
- [Epic & Story Structure](./brownfield-prd/epic-and-story-structure.md)
- [Epic 1: Production-Ready MVP](./brownfield-prd/epic-1-complete-production-ready-mvp-with-standalone-observability.md)

### User Stories
Access detailed user stories in the [stories directory](./stories/index.md):
- OpenTelemetry Handler Implementation
- Message Bus Enhancement
- LLM Contract Standardization
- Test Coverage (Core & Providers)
- Documentation Integration

## Component Documentation

- [Observability System](../src/llmgine/observability/README.md) - Standalone observability architecture
- [Message Bus](../src/llmgine/bus/README.md) - Event and command bus architecture
- [Tools System](../src/llmgine/llm/tools/README.md) - Function calling and tool registration

## Observability Documentation

- [Architecture Guide](./observability-architecture.md) - Design decisions and performance analysis
- [Migration Guide](./observability-migration-guide.md) - Upgrading from EventLogWrapper
- [Cookbook](./observability-cookbook.md) - Practical recipes and examples

## Quick Links

- [Main README](../README.md) - Getting started and overview
- [CLAUDE.md](../CLAUDE.md) - AI assistant instructions