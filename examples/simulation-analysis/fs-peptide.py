"""Use a simulation-analysis loop to manage an array of simulations until a peptide folds.

After installing GROMACS and gmxapi, execute this script with a Python 3.8+ interpreter.

For a trajectory ensemble, use `mpiexec` and `mpi4py`. For example, for an ensemble of
size 50, activate your gmxapi Python virtual environment and run

    mpiexec -n 50 `which python` -m mpi4py fs-peptide.py --cores 50

"""
import argparse
import logging
import os
from pathlib import Path

# Set up a command line argument processor for our script.
parser = argparse.ArgumentParser()
parser.add_argument(
    '--cores',
    default=os.cpu_count(),
    type=int,
    help='The total number of cores allocated for the job.'
)
parser.add_argument(
    '--maxh',
    type=float,
    default=0.1,
    help='Maximum time for a single simulation in this module.'
)
parser.add_argument(
    '--inputs',
    type=Path,
    default=Path(__file__).resolve().parent.parent.parent / 'input_files' / 'fs-peptide',
    help='Directory containing fs-peptide input files.'
)
parser.add_argument(
    '--max-iterations',
    type=int,
    default=10,
    help='Maximum number of iterations for the simulation-analysis loop.'
)
parser.add_argument(
    '--log-level',
    default='ERROR',
    help='Minimum log level to handle for the Python "logging" module. (See '
         'https://docs.python.org/3/library/logging.html#logging-levels)'
)


def main(*, input_dir: Path, maxh: float, threads_per_rank: int, ensemble_size: int, max_iterations: int):
    """Define the main work for this script."""

    from fold import make_top, make_simulation_input, fold

    # Confirm inputs exist
    if not all(p.exists() for p in (input_dir, input_dir / 'start0.pdb', input_dir / 'ref.pdb')):
        raise RuntimeError(f'Did not find input files in {input_dir}.')
    reference_struct = input_dir / 'ref.pdb'

    topology_source = make_top(input_dir=input_dir)
    logging.info('Created a handle to a commandline operation.')

    simulation_input = make_simulation_input(
        topology=topology_source,
        ensemble_size=ensemble_size,
        input_dir=input_dir)
    assert simulation_input.output.ensemble_width == ensemble_size

    folding_loop = fold(simulation_input,
                        maxh=maxh,
                        max_iterations=max_iterations,
                        threads_per_rank=threads_per_rank,
                        reference_struct=reference_struct)
    folding_loop.run()
    return folding_loop


if __name__ == '__main__':
    try:
        from mpi4py import MPI

        rank_number = MPI.COMM_WORLD.Get_rank()
        comm_size = MPI.COMM_WORLD.Get_size()
    except ImportError:
        rank_number = 0
        comm_size = 1
        rank_tag = ''
        MPI = None
    else:
        rank_tag = 'rank{}:'.format(rank_number)
    # Handle command line invocation.
    args = parser.parse_args()

    # Configure logging module before importing tools that use it.
    logging.basicConfig(level=str(args.log_level).upper())

    # Update the logging output.
    log_format = '%(levelname)s %(name)s:%(filename)s:%(lineno)s %(rank_tag)s%(message)s'
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter(log_format))

    allocation_size = args.cores
    try:
        local_cpu_set_size = len(os.sched_getaffinity(0))
    except (NotImplementedError, AttributeError):
        threads_per_rank = allocation_size // comm_size
    else:
        threads_per_rank = min(local_cpu_set_size, allocation_size // comm_size)

    # Call the main work.
    folding_loop = main(
        input_dir=args.inputs,
        maxh=args.maxh,
        ensemble_size=comm_size,
        threads_per_rank=threads_per_rank,
        max_iterations=args.max_iterations)

    found_native = folding_loop.output.found_native.result()
    min_rms = folding_loop.output.min_rms.result()
    logging.debug(f'found_native: {found_native}')
    logging.debug(f'min_rms: {min_rms}')

    if comm_size > 1:
        assert isinstance(found_native, list)
        found_native = any(found_native)
        assert isinstance(min_rms, list)
        min_rms = min(min_rms)
    else:
        assert comm_size == 1
        assert isinstance(found_native, bool)
        assert isinstance(min_rms, float)

    if rank_number == 0:
        if found_native:
            print('Found native conformation, according to convergence condition.')
        else:
            print('No trajectories converged on the target conformation.')
        print(f'Minimum rms difference from target structure: {min_rms}')
