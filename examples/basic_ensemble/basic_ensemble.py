"""Prepare and run an ensemble of trajectories.

After installing GROMACS and gmxapi, execute this script with a
Python 3.8+ interpreter.

For the trajectory ensemble, use ``mpiexec`` and ``mpi4py``.

For example, for an ensemble of size 50, activate your gmxapi Python virtual
environment and run::

    mpiexec -n 50 `which python` -m mpi4py fs-peptide.py --cores 50

"""

import argparse
import logging
import os
from pathlib import Path

# Configure logging module before importing tools that use it.
logging.basicConfig(level=logging.INFO)

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
    default=Path(__file__).parent.parent.parent.resolve() / 'input_files' / 'fs-peptide',
    help='Directory containing fs-peptide input files.'
)


def main(*, input_dir: Path, maxh: float, ensemble_size: int, threads_per_rank: int):
    """Figure 1b: gmxapi command on ensemble input

    Call the GROMACS MD preprocessor to create a simulation input file. Declare an
    ensemble simulation workflow starting from the single input file.

    Args:
        make_top operation handle, as generated in `figure1a`

    Returns:
        Trajectory output. (list, if ensemble simulation)
    """
    import gmxapi as gmx

    args = ['pdb2gmx', '-ff', 'amber99sb-ildn', '-water', 'tip3p']
    input_files = {'-f': os.path.join(input_dir, 'start0.pdb')}
    output_files = {
            '-p': 'topol.top',
            '-i': 'posre.itp',
            '-o': 'conf.gro'}
    make_top = gmx.commandline_operation('gmx', args, input_files, output_files)

    # Optionally, confirm inputs exist:
    # make_top.run()
    # assert os.path.exists(make_top.output.file['-o'].result())
    # assert os.path.exists(make_top.output.file['-p'].result())

    cmd_dir = input_dir
    assert os.path.exists(input_dir / 'grompp.mdp')

    # Figure 1b code.
    grompp_input_files = {'-f': os.path.join(cmd_dir, 'grompp.mdp'),
                          '-c': make_top.output.file['-o'],
                          '-p': make_top.output.file['-p']}

    # make array of inputs
    N = ensemble_size
    grompp = gmx.commandline_operation(
        'gmx',
        ['grompp'],
        input_files=[grompp_input_files] * N,
        output_files={'-o': 'run.tpr'})
    tpr_input = grompp.output.file['-o'].result()

    input_list = gmx.read_tpr(tpr_input)

    md = gmx.mdrun(input_list, runtime_args={'-maxh': str(maxh), '-nt': str(threads_per_rank)})
    md.run()

    return {
        'input_list': input_list,
        'trajectory': md.output.trajectory.result()
    }


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

    # Update the logging output.
    log_format = '%(levelname)s %(name)s:%(filename)s:%(lineno)s %(rank_tag)s%(message)s'
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter(log_format))

    # Handle command line invocation.
    args = parser.parse_args()

    allocation_size = args.cores
    try:
        local_cpu_set_size = len(os.sched_getaffinity(0))
    except (NotImplementedError, AttributeError):
        threads_per_rank = allocation_size // comm_size
    else:
        threads_per_rank = min(local_cpu_set_size, allocation_size // comm_size)

    # Call the main work.
    main(input_dir=args.inputs, maxh=args.maxh, ensemble_size=comm_size, threads_per_rank=threads_per_rank)
