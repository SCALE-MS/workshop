"""Prepare and run an ensemble of trajectories.

After installing GROMACS and gmxapi, execute this script with a
Python 3.8+ interpreter.

For the trajectory ensemble, use ``mpiexec`` and ``mpi4py``.

For example, for an ensemble of size 50, activate your gmxapi Python virtual
environment and run::

    mpiexec -n 50 `which python` -m mpi4py basic_example.py --cores 50

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
    '--log-level',
    default='ERROR',
    help='Minimum log level to handle for the Python "logging" module. (See '
         'https://docs.python.org/3/library/logging.html#logging-levels)'
)


def main(*, input_dir: Path, maxh: float, ensemble_size: int, threads_per_rank: int):
    """Gromacs simulation on ensemble input

    Call the GROMACS MD preprocessor to create a simulation input file. Declare an
    ensemble simulation workflow starting from the single input file.

    Args:
        input_dir: path to the fs-peptide input files
        maxh: maximum wall time for the simulations
        ensemble_size: number of independent trajectories
        threads_per_rank: CPU threads per simulation ('-nt' argument)

    Returns:
        Trajectory output. (list, if ensemble simulation)
    """
    import gmxapi as gmx
    import scalems_workshop as scalems

    commandline = [
        gmx.commandline.cli_executable(), 'pdb2gmx', '-ff', 'amber99sb-ildn', '-water', 'tip3p',
        '-f', os.path.join(input_dir, 'start0.pdb'),
        '-p', scalems.output_file('topol.top'),
        '-i', scalems.output_file('posre.itp'),
        '-o', scalems.output_file('conf.gro')
    ]
    make_top = scalems.executable(commandline)

    # make array of inputs
    commandline = [
        gmx.commandline.cli_executable(),
        'grompp',
        '-f', os.path.join(input_dir, 'grompp.mdp'),
        # TODO: executable task output proxy
        # '-c', make_top.output_file['conf.gro'],
        # '-p', make_top.output_file['topol.top'],
        '-c', make_top.output.file['-o'],
        '-p', make_top.output.file['-p'],
        '-o', scalems.output_file('run.tpr', label='simulation_input')
    ]
    grompp = scalems.executable([commandline] * ensemble_size)

    # TODO: executable task output proxy
    # tpr_input = grompp.output_file['simulation_input']
    tpr_input = grompp.output.file['-o']

    input_list = gmx.read_tpr(tpr_input)

    md = gmx.mdrun(input_list, runtime_args={'-maxh': str(maxh), '-nt': str(threads_per_rank)})
    md.run()

    return md.output.trajectory.result()


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
    # else:
    #     rank_tag = 'rank{}:'.format(rank_number)

    # Handle command line invocation.
    args = parser.parse_args()

    # Configure logging module before importing tools that use it.
    logging.basicConfig(level=str(args.log_level).upper())

    # Update the logging output.
    # The `rank_tag` definition is provided by gmxapi
    # log_format = '%(levelname)s %(name)s:%(filename)s:%(lineno)s %(rank_tag)s%(message)s'
    log_format = '%(levelname)s %(name)s:%(filename)s:%(lineno)s %(message)s'
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter(log_format))

    if rank_number == 0:
        logging.info(f'Input directory set to {args.inputs}.')

    allocation_size = args.cores
    try:
        local_cpu_set_size = len(os.sched_getaffinity(0))
    except (NotImplementedError, AttributeError):
        threads_per_rank = allocation_size // comm_size
    else:
        threads_per_rank = min(local_cpu_set_size, allocation_size // comm_size)

    # Call the main work.
    trajectory = main(
        input_dir=args.inputs,
        maxh=args.maxh,
        ensemble_size=comm_size,
        threads_per_rank=threads_per_rank)

    if not isinstance(trajectory, list):
        trajectory = [trajectory]

    if rank_number == 0:
        for i, out in enumerate(trajectory):
            print(f'Trajectory {i}: {out}')
