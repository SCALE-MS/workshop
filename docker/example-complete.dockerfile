# Provide a complete environment in a single image.
#
# Runs a mongodb server when launched with the default command.
#
# Includes LAMMPS, GROMACS, RCT, and SCALE-MS software, with a self-contained
# RADICAL Pilot client and execution environment.
#
# Summary:
#     docker run --rm -ti -u rp scalems/example-complete bash -c '. rp-venv/bin/activate; \
#          mkdir -p exercise1 && cd exercise1 && mpiexec -n 2 `which python` -m mpi4py \
#          ~/scalems-workshop/examples/basic_ensemble/basic_ensemble.py --maxh 0.001 && find .'
#
# To build and use the all-in-one container for SCALE-MS on RADICAL Pilot:
#     docker build -t scalems/example-complete -f example-complete.dockerfile ..
#        # or
#     docker pull scalems/example-complete
#        # then
#     docker run --rm --name scalems_test -d scalems/example-complete
#        # then, afterwards,
#     docker stop scalems_test
#
# Note regarding M1 Macs (and other non-x86_64 architectures):
#
# Make sure you Docker Desktop and the `docker` command line tools for the
# correct architecture.
#
# Then, the `docker` command should automatically pull the most appropriate image
# for your architecture. You can confirm by comparing the architecture of the
# pulled image by running it with `uname -m`:
#     docker run --rm scalems/example-complete uname -m
# If it gives the wrong output, you can either pull a specific digest
# from https://hub.docker.com/r/scalems/example-complete/tags
# or you can `pull` or `run` the image for a specific architecture
# (if available) with the `--platform` argument.
# E.g.
#     docker pull --platform arm64 scalems/example-complete
#
# Updating Docker Hub
#
# To build multi-architecture images, use `buildx`:
#     docker buildx build --platform linux/arm64/v8,linux/amd64 -t scalems/example-complete -f example-complete.dockerfile --push ..
# See also:
#  * https://docs.docker.com/desktop/multi-arch/
#  * https://docs.docker.com/buildx/working-with-buildx/
# Warning: The non-native architecture will build much more slowly, but the
# performance difference of having a native architecture at run time is profound.
#
# Prerequisites:
#
# Before building this image, pull the `scalems/lammps` and `scalems/gromacs` images.
#     docker pull scalems/lammps && docker pull scalems/gromacs
#
# Using this image:
#
# For RADICAL Pilot use cases, the MongoDB server needs to be running. To start
# the container with a MongoDB service, start it in a detached / daemon mode
# with the default user and default command.
#
# Then connect as the "rp" user to run a bash shell. Don't forget to activate
# the `~rp/rp-venv` Python virtual environment.
#
# If you are sure you don't need RADICAL Pilot (and MongoDB), then you can use
# the container normally, but you must provide an explicit command or the
# container will just leave you interacting with the MongoDB server process.
#
# Example usage (Python+LAMMPS only):
#     docker run --rm -ti -u rp scalems/example-complete bash
#     $ . ./rp-venv/bin/activate
#     $ $RPVENV/bin/lmp ...
#
# Example usage (Python+gmxapi):
#     docker run --rm -ti -u rp scalems/example-complete bash
#     $ . ./rp-venv/bin/activate
#     $ python
#     >>> import gmxapi as gmx
#
# Example usage with RP availability:
# The mongodb server needs to be running, so start the container, wait for mongodb to start,
# and then launch a shell as an additional process.
#
# 1. Launch the container (as root, so that the mongod can be started).
# 2. Wait a few seconds for the MongoDB service to start.
# 3. Exec the tests in the container.
# 4. Stop or kill the container.
#
#     docker run --rm --name scalems_test -d scalems/example-complete
#     sleep 3
#     docker exec -ti -u rp scalems_test bash -c ". rp-venv/bin/activate && python -m pytest scalems/tests --rp-resource local.localhost --rp-venv \$VIRTUAL_ENV"
#     docker exec -ti -u rp scalems_test bash -c ". rp-venv/bin/activate && python -m scalems.radical --resource=local.localhost --venv /home/rp/rp-venv scalems/examples/basic/echo.py hi there"
#     docker stop scalems_test

# Prerequisite: build base images from https://github.com/SCALE-MS/scale-ms/tree/master/docker
ARG TAG=latest
FROM scalems/lammps:$TAG

COPY --from=scalems/gromacs $RPVENV/gromacs $RPVENV/gromacs

USER rp

ARG GMXAPI_REF="gmxapi"
RUN . $RPVENV/gromacs/bin/GMXRC && $RPVENV/bin/pip install $GMXAPI_REF

# Use a custom definition of `local.localhost`.
COPY --chown=rp:radical docker/resource_local.json /home/rp/.radical/pilot/configs/resource_local.json

# Update workshop material.
COPY --chown=rp:radical . /home/rp/scalems-workshop

# Update workshop environment.
# TODO: Install workshop package from cloud or source archive.
COPY --chown=rp:radical .git /home/rp/scalems-workshop/.git
RUN $RPVENV/bin/pip install --upgrade pip setuptools wheel
RUN $RPVENV/bin/pip install /home/rp/scalems-workshop
RUN $RPVENV/bin/pip uninstall -y radical.pilot radical.saga radical.utils

# Update scalems
# Avoid ambiguity from installation inherited from scalems/lammps image.
RUN rm -rf /home/rp/scalems
RUN . $RPVENV/bin/activate && pip install -r /home/rp/scalems-workshop/external/scale-ms/requirements-testing.txt
RUN $RPVENV/bin/pip install --no-deps --no-build-isolation -e /home/rp/scalems-workshop/external/scale-ms

# Restore the user for the default entry point (the mongodb server)
USER mongodb
