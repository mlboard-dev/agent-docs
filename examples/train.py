"""Explicitly run a small synthetic integration check after user authorization."""
import os
import uuid
import mlboard


def main():
    server = os.environ['MLBOARD_SERVER']
    project = os.environ['MLBOARD_PROJECT_ID']
    # Do not print this value or put it in the Run config.
    os.environ['MLBOARD_API_KEY']
    run = mlboard.init(
        project=project,
        run_path='agent-example/' + uuid.uuid4().hex[:12],
        server=server,
        sync='background',
        spool_dir='./outputs/mlboard-runs',
        config={'synthetic': True},
        tags=['synthetic', 'agent-integration-check'],
    )
    for step in range(10):
        receipt = run.log({'train/loss': 1.0 / (step + 1)}, step=step)
        if not receipt.accepted:
            raise RuntimeError('Training record was not accepted: ' + str(receipt.reason))
    result = run.finish(wait_for='remote', timeout=120)
    if not result.complete or result.dropped:
        raise RuntimeError('Remote completion was not confirmed: ' + str(result.reason))
    print('Remote completion confirmed for Run', run.id)


if __name__ == '__main__':
    main()
