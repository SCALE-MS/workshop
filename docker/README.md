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
docker exec -ti -u rp scalems_test bash -c '. rp-venv/bin/activate && python -m scalems.radical --resource=local.localhost --venv $VIRTUAL_ENV --log-level debug scalems/examples/basic/echo.py hi there && cat 0*0/stdout'
docker stop scalems_test
```
