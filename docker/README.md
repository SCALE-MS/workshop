# Docker images

The `scalems.radical` execution module requires RADICAL Pilot (RP). RP requires
a MongoDB database instance to operate.

We derive some self-contained Docker images from
[scalems/rp-complete](https://hub.docker.com/r/scalems/rp-complete),
which, in turn, is based on the https://hub.docker.com/_/mongo image.

For more complex environments, we use Docker Compose.

See https://github.com/SCALE-MS/scale-ms/tree/master/docker

## scalems/example-complete

`example-complete.dockerfile` provides a RADICAL Pilot environment with a MongoDB server,
and installations of GROMACS, LAMMPS, gmxapi, and scalems in the `/home/rp/rp-venv`
Python virtual environment for the `rp` user.
Refer to the file contents for usage details.

## Examples

### Example 00

Execute a decorated function from a Python module file.

```shell
docker build -t scalems/example-complete -f example-complete.dockerfile .
docker run --rm --name scalems_test -d scalems/example-complete
# The MongoDB server needs a few moments to start up.
sleep 3
docker exec -ti -u rp -e HOME=/home/rp scalems_test bash -c '. rp-venv/bin/activate && python -m scalems.radical --resource=local.localhost --venv $VIRTUAL_ENV --log-level debug scalems-workshop/external/scale-ms/examples/basic/echo.py hi there && cat 0*0/stdout'
docker stop scalems_test
```

### Example 01

Run a simulation or array of simulations from a script.

Replace `2` with an appropriate ensemble size. Remove or update the `--maxh` option for desired simulation length.

```shell
docker build -t scalems/example-complete -f example-complete.dockerfile ..
docker run --rm -ti -u rp -e HOME=/home/rp scalems/example-complete bash -c \
'. rp-venv/bin/activate; mkdir exercise1 && cd exercise1 && mpiexec -n 2 `which python` -m mpi4py ~/scalems-workshop/examples/basic_ensemble/basic_ensemble.py --maxh 0.001'
```

### Example 01.1

Run a simulation or array of simulations from a script.

Note that the raptor task and worker will consume at least 2 cores from the pilot allocation.

Replace `size` with an appropriate ensemble size. Remove or update the `maxh` *mdrun-arg* for desired simulation length.

```shell
cd external/scale-ms/docker
# Use the following line if and only if you need a non-default gromacs build.
docker compose build --build-arg GROMACS_SUFFIX=_mpi login compute
docker compose up -d
docker compose cp ../../../ login:/home/rp/
docker compose exec login bash -c 'chown -R rp:radical /home/rp'
docker compose exec -ti -u rp -e HOME=/home/rp login bash
```

Then, in the container environment:

```shell
. rp-venv/bin/activate
pip install -r scalems-workshop/external/scale-ms/requirements-testing.txt
pip install -e scalems-workshop/external/scale-ms
pip install -e scalems-workshop
mkdir exercise1
cd exercise1
python ~/scalems-workshop/examples/basic_ensemble/rp_basic_ensemble.py \
  --resource docker.login \
  --access ssh \
  --venv $VIRTUAL_ENV \
  --procs-per-sim 1 \
  --pilot-option cores=4 \
  --size 2 \
  --mdrun-arg maxh 0.001 \
  --enable-raptor
```

### Example 02

Run a simulation-ensemble-analysis loop from a script.

Replace `2` with an appropriate ensemble size. Remove or update the `--maxh` option for wall-time of individual simulation segments.
Note that if simulation segments are too short, there will be no data to analyse.
Refer to the `fs-peptide.py` source or use the `--help` flag
for other run time options.

```shell
docker build -t scalems/example-complete -f example-complete.dockerfile ..
docker run --rm -ti -u rp -e HOME=/home/rp scalems/example-complete bash -c \
'. rp-venv/bin/activate; mkdir exercise2 && cd exercise2 && mpiexec -n 2 `which python` -m mpi4py ~/scalems-workshop/examples/simulation-analysis/fs-peptide.py --maxh 0.001'
```
