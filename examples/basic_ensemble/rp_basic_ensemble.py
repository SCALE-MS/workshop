"""Prepare and run an ensemble of trajectories through RADICAL Pilot.

We will rely on RADICAL Pilot to manage resource allocation. For simplicity,
this example assumes that the local.localhost RP resource is configured appropriately,
and that the "local" access scheme is sufficient.

This example is tested with thread-MPI GROMACS. MPI parallelism in scalems.radical
tasks is under investigation.

The *cores-per-sim* must not exceed the cores available to the pilot.

For example, for an ensemble of size 2, activate your gmxapi Python virtual
environment and run::

    python rp_basic_ensemble.py \
        --resource local.localhost \
        --access local \
        --venv $VIRTUAL_ENV \
        --pilot-option cores=4 \
        --cores-per-sim 2 \
        --size 2 \
        --maxh 1.0

"""
from __future__ import annotations

import asyncio
import argparse
import logging
import os
import sys
import typing
from pathlib import Path

import scalems
import scalems.call
import scalems.radical
import scalems.workflow


class MDRunResult(typing.TypedDict):
    """Return type for the MDRun Command."""
    trajectory: str
    directory: str


async def main(*, input_dir: Path, maxh: float, ensemble_size: int, threads_per_rank: int, manager: scalems.workflow.WorkflowManager, label: str) -> tuple[MDRunResult]:
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
    import scalems_workshop as workshop

    commandline = [
        gmx.commandline.cli_executable(), 'pdb2gmx', '-ff', 'amber99sb-ildn', '-water', 'tip3p',
        '-f', os.path.join(input_dir, 'start0.pdb'),
        '-p', workshop.output_file('topol.top'),
        '-i', workshop.output_file('posre.itp'),
        '-o', workshop.output_file('conf.gro')
    ]
    make_top = workshop.executable(commandline)

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
        '-o', workshop.output_file('run.tpr', label='simulation_input')
    ]
    grompp = workshop.executable([commandline])

    # TODO: executable task output proxy
    # tpr_input = grompp.output_file['simulation_input']
    tpr_input = grompp.output.file['-o'].result()

    session: scalems.radical.runtime.RPDispatchingExecutor
    async with manager.dispatch() as session:
        simulations = tuple(
            MDRun(tpr_input, maxh=maxh, threads_per_sim=threads_per_rank, manager=manager, dispatcher=session,
                  label=f"{label}-{i}") for i in range(ensemble_size)
        )
        futures = tuple(asyncio.create_task(md.result(), name=md.label) for md in simulations)
        for future in futures:
            future.add_done_callback(lambda x: print(f"Task done: {repr(x)}."))
        return await asyncio.gather(*futures)


class MDRun:
    """Instance of a simulation Command."""

    def __init__(self, input, *, maxh: float, threads_per_sim: int, label: str,
            manager: scalems.workflow.WorkflowManager, dispatcher: scalems.radical.runtime.RPDispatchingExecutor, ):
        self.label = label
        # TODO: Manage input file staging so we don't have to assume localhost.
        args = (input,)
        kwargs = dict(
            runtime_args={'-maxh': str(maxh), '-nt': str(threads_per_sim)
            }
        )
        requirements = {"ranks": 1, "cores_per_rank": threads_per_sim, "threading_type": "OpenMP"}
        task_uid = label
        self._call_handle: asyncio.Task[scalems.call._Subprocess] = asyncio.create_task(
            scalems.call.function_call_to_subprocess(
                func=self._func, label=task_uid, args=args, kwargs=kwargs, manager=manager, requirements=requirements
            )
        )
        self._dispatcher = dispatcher

    @staticmethod
    def _func(simulation_input, *, runtime_args=None):
        """Task implementation."""
        from gmxapi import mdrun
        if runtime_args is None:
            runtime_args = {}
        md = mdrun(simulation_input, runtime_args=runtime_args)
        return md.output.trajectory.result()

    async def result(self) -> MDRunResult:
        """Deliver the results of the simulation Command."""
        # Wait for input preparation
        call_handle = await self._call_handle
        rp_task_result_future = asyncio.create_task(
            scalems.radical.runtime.subprocess_to_rp_task(call_handle, dispatcher=self._dispatcher)
        )
        # Wait for submission and completion
        rp_task_result = await rp_task_result_future
        result_future = asyncio.create_task(
            scalems.radical.runtime.wrapped_function_result_from_rp_task(call_handle, rp_task_result)
        )
        # Wait for results staging.
        result: scalems.call.CallResult = await result_future
        # Note that the return_value is the trajectory path in the RP-managed Task directory.
        # TODO: stage trajectory file, explicitly?
        return {"trajectory": result.return_value, "directory": result.directory}


if __name__ == '__main__':
    import scalems.radical
    # Set up a command line argument processor for our script.
    # Inherit from the backend parser so that `parse_known_args` can handle positional arguments the way we want.
    parser = argparse.ArgumentParser(parents=[scalems.radical.parser], add_help=False)

    parser.add_argument('--cores-per-sim', type=int, help='The total number of cores allocated for the job.')
    parser.add_argument('--maxh', type=float, default=0.01, help='Maximum time for a single simulation in this module.')
    parser.add_argument('--inputs', type=Path,
        default=Path(__file__).resolve().parent.parent.parent / 'input_files' / 'fs-peptide',
        help='Directory containing fs-peptide input files.')
    # parser.add_argument('--log-level', default='ERROR',
    #     help='Minimum log level to handle for the Python "logging" module. (See '
    #          'https://docs.python.org/3/library/logging.html#logging-levels)')
    parser.add_argument("--size", type=int, default=1, help="Ensemble size: number of parallel pipelines.")

    # Work around some quirks: we are using the parser that normally assumes the
    # backend from the command line. We can switch back to the `-m scalems.radical`
    # style invocation when we have some more updated UI tools
    # (e.g. when scalems.wait has been updated) and `main` doesn't have to be a coroutine.
    sys.argv.insert(0, __file__)

    # Handle command line invocation.
    config, argv = parser.parse_known_args()

    # Configure logging module before using tools that use it.
    level = None
    debug = False
    if config.log_level is not None:
        level = logging.getLevelName(config.log_level.upper())
        debug = level <= logging.DEBUG
    if level is not None:
        character_stream = logging.StreamHandler()
        character_stream.setLevel(level)
        formatter = logging.Formatter("%(asctime)s-%(name)s:%(lineno)d-%(levelname)s - %(message)s")
        character_stream.setFormatter(formatter)
        logging.basicConfig(level=level, handlers=[character_stream])

    logging.info(f'Input directory set to {config.inputs}.')

    # Call the main work.
    manager = scalems.radical.workflow_manager(asyncio.get_event_loop())
    with scalems.workflow.scope(manager, close_on_exit=True):
        md_outputs = asyncio.run(
            main(
                input_dir=config.inputs,
                maxh=config.maxh,
                threads_per_rank=config.cores_per_sim,
                manager=manager,
                ensemble_size=config.size,
                label="rp-basic-ensemble"),
            debug=debug)

    trajectory = [md["trajectory"] for md in md_outputs]
    directory = [md["directory"] for md in md_outputs]

    for i, out in enumerate(zip(trajectory, directory)):
        print(f'Trajectory {i}: {out[0]}. Directory archive (zip file) {i}: {out[1]}')
