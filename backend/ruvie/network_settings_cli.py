"""Operator-only, one-shot F018 cutover of BOTH legacy proxy routes.

Run after migration 0014 with old application/worker processes stopped.
Never prints proxy endpoints, keys or SQL bound values.
"""
import argparse
import os
from sqlalchemy import select, update
from ruvie.config import load_settings
from ruvie.database import create_database_engine, create_session_factory
from ruvie.models import OrganizationLlmSettings, OrganizationEmbeddingSettings
from ruvie.adapters.network import InvalidNetworkConfiguration, NetworkConfigurationPendingError
from ruvie.contracts.network import NetworkConfig
from ruvie.services.admin import AdminAccountService
from ruvie.services.audit import AuditEventWriter

def legacy_network(name: str) -> NetworkConfig:
    value = os.getenv(name, '').strip()
    if not value:
        return NetworkConfig(mode='direct', proxy_url=None)
    return NetworkConfig(mode='proxy', proxy_url=value)

def convert(session, actor_id: str, llm_version: int, embedding_version: int,
            llm_network: NetworkConfig, embedding_network: NetworkConfig) -> bool:
    """All-or-nothing, expected-version and actor-checked; returns False if done."""
    try:
        AdminAccountService(session).require_admin(actor_id, lock=True)
        rows = [
            (OrganizationLlmSettings, llm_version, llm_network, 'llm.organization_network.cutover', 'organization_llm'),
            (OrganizationEmbeddingSettings, embedding_version, embedding_network, 'embedding.organization_network.cutover', 'organization_embedding'),
        ]
        current = [session.scalar(select(model).where(model.id == 1).with_for_update())
                   for model, _, _, _, _ in rows]
        if any(row is None for row in current):
            raise NetworkConfigurationPendingError()
        if all(row.network_mode is not None for row in current):
            session.rollback()
            return False  # Idempotent: never overwrite an administrator's later choice.
        if any(row.network_mode is not None for row in current):
            raise NetworkConfigurationPendingError()
        if any(row.version != expected for row, (_, expected, _, _, _) in zip(current, rows)):
            raise ValueError('configuration_conflict')
        for row, (model, expected, network, action, resource_type) in zip(current, rows):
            new_version = expected + 1 if expected > 0 else 0
            changed = session.execute(update(model).where(
                model.id == 1, model.version == expected, model.network_mode.is_(None),
            ).values(network_mode=network.mode, proxy_url=network.proxy_url,
                     version=new_version, updated_by=actor_id))
            if changed.rowcount != 1:
                raise ValueError('configuration_conflict')
            AuditEventWriter.append(session, actor_id, action=action,
                                    resource_type=resource_type, resource_id='1', outcome='allow',
                                    reason=f'version:{expected}->{new_version};network:{network.mode}')
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise

def main(argv=None):
    parser = argparse.ArgumentParser(description='F018 atomic legacy proxy cutover')
    parser.add_argument('--confirm', action='store_true', help='Write both routes after a dry run')
    parser.add_argument('--actor-id', help='Active admin ID (required for --confirm)')
    parser.add_argument('--llm-version', type=int, help='Version confirmed in dry-run')
    parser.add_argument('--embedding-version', type=int, help='Version confirmed in dry-run')
    args = parser.parse_args(argv)
    if args.confirm and (not args.actor_id or args.llm_version is None or args.embedding_version is None):
        parser.error('--confirm requires --actor-id, --llm-version and --embedding-version')
    engine = None
    try:
        settings = load_settings()  # Loads original deployment environment for this CLI only.
        llm_network = legacy_network('LLM_PROXY_URL')
        embedding_network = legacy_network('EMBEDDING_PROXY_URL')
        engine = create_database_engine(settings.database_url)
        factory = create_session_factory(engine)
        with factory() as session:
            states = [session.get(OrganizationLlmSettings, 1), session.get(OrganizationEmbeddingSettings, 1)]
            if any(row is None for row in states):
                raise NetworkConfigurationPendingError()
            print('LLM: mode=%s rows=1 version=%s pending=%s' %
                  (llm_network.mode, states[0].version, states[0].network_mode is None))
            print('Embedding: mode=%s rows=1 version=%s pending=%s' %
                  (embedding_network.mode, states[1].version, states[1].network_mode is None))
            session.rollback()
        if args.confirm:
            with factory() as session:
                changed = convert(session, args.actor_id, args.llm_version,
                                  args.embedding_version, llm_network, embedding_network)
            print('Cutover committed' if changed else 'Already converted; no changes')
        else:
            print('Dry-run only; pass --confirm with active admin ID and both versions after maintenance')
        return 0
    except (ValueError, InvalidNetworkConfiguration, NetworkConfigurationPendingError):
        print('Cutover refused: invalid, pending, or conflicting configuration')
        return 2
    except Exception:
        print('Cutover failed safely; no endpoints or secrets have been logged')
        return 2
    finally:
        if engine is not None:
            engine.dispose()

if __name__ == '__main__':
    raise SystemExit(main())
