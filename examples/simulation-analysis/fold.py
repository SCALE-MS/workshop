"""Support module for fs-peptide folding script.

After installing GROMACS and gmxapi, make sure this file is importable in your
execution environment, along with the scalems_workshop support package.
"""
import logging
import os

# Configure logging module before gmxapi.
from pathlib import Path

logging.basicConfig(level=logging.INFO)

import gmxapi as gmx
import scalems_workshop as scalems
from scalems_workshop import numeric_min, xvg_to_array, less_than, subgraph

logging.info(f'gmxapi Python package version {gmx.__version__}')
assert gmx.version.has_feature('mdrun_runtime_args')
assert gmx.version.has_feature('container_futures')
assert gmx.version.has_feature('mdrun_checkpoint_output')

# Update the logging output.
log_format = '%(levelname)s %(name)s:%(filename)s:%(lineno)s %(rank_tag)s%(message)s'
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter(log_format))


def make_top(*, input_dir):
    """Wrapped command-line operation to provide topology.

    Prepare a molecular model from a PDB file using the `pdb2gmx` GROMACS tool.
    """
    commandline = [
        gmx.commandline.cli_executable(),
        'pdb2gmx', '-ff', 'amber99sb-ildn', '-water', 'tip3p',
        '-f', os.path.join(input_dir, 'start0.pdb'),
        '-p', scalems.output_file(label='topology', suffix='.top'),
        '-i', scalems.output_file(label='restraints', suffix='.itp'),
        '-o', scalems.output_file(label='conformation', suffix='.gro')
    ]
    topology = scalems.executable(commandline)
    return topology


def make_simulation_input(*, topology_source, ensemble_size, input_dir):
    """Set up the ensemble simulation input.

    Call the GROMACS MD preprocessor to create a simulation input file. Declare an
    ensemble simulation workflow starting from the single input file.

    Args:
        topology_source: handle to the topology creation operation (pdb2gmx)
        ensemble_size: number of simulation inputs
        input_dir: path to fs-peptide input files

    Returns:
        Handle to the ensemble simulation input.
    """
    cmd_dir = input_dir
    assert os.path.exists(input_dir / 'grompp.mdp')
    parameters = os.path.join(cmd_dir, 'grompp.mdp')

    topology = topology_source.output_file['topology']
    conformation = topology_source.output_file['conformation']

    commandline = [
        gmx.commandline.cli_executable(), 'grompp',
        '-f', parameters,
        '-c', conformation,
        '-p', topology,
        '-o', scalems.output_file(label='simulation_input', suffix='.tpr')
    ]

    # make array of inputs
    N = ensemble_size
    grompp = scalems.executable([commandline] * N)
    tpr_input = grompp.output_file['simulation_input']

    input_list = gmx.read_tpr(tpr_input)
    return input_list


def fold(simulation_input, *, maxh: float, threads_per_rank: int, reference_struct: Path, max_iterations: int):
    """Simulation-analysis loop finds the first ensemble member to fold the input molecule.

    Args:
        simulation_input: ensemble simulation input handle
        maxh: maximum wall time for each simulation iteration
        threads_per_rank: CPU threads per simulation ('-nt' argument)
        reference_struct: structure (PDB file path) identifying the folded state.
        max_iterations: maximum number of iterations to perform in the simulation-analysis loop

    Returns:
        Handle to the (completed) while_loop operation.
    """
    class SimulationAnalysis(subgraph.Subgraph):
        found_native = subgraph.output_variable(default=False)
        checkpoint = subgraph.output_variable(default='')
        min_rms = subgraph.output_variable(default=1e6)

        # Decorate a non-scalems command so that the framework knows to convert
        # the subgraph variable to native type when calling during iteration.
        md = subgraph.add(
            gmx.mdrun,
            simulation_input,
            runtime_args={
                '-cpi': checkpoint.get(),
                '-maxh': str(maxh),
                '-noappend': None,
                '-nt': str(threads_per_rank)
            })

        # Establish a node (internal data flow), updating a subgraph variable.
        checkpoint.set(md.output.checkpoint)

        rmsd = scalems.executable(
            [
                gmx.commandline.cli_executable(),
                'rms', '-s', reference_struct, '-f', md.output.trajectory,
                '-o', scalems.output_file('rmsd.xvg')
            ],
            stdin='Backbone Backbone\n'
        )

        min_rms.set(numeric_min(xvg_to_array(rmsd.output_file['data'])))
        found_native.set(less_than(lhs=min_rms.get(), rhs=0.3))

    folding_loop = scalems.while_loop(operation=SimulationAnalysis,
                                      condition=scalems.logical_not(SimulationAnalysis.found_native),
                                      max_iteration=max_iterations)()
    logging.info('Beginning folding_loop.')
    folding_loop.run()
    logging.info(f'Finished folding_loop. min_rms: {folding_loop.output.min_rms.result()}')
    return folding_loop
