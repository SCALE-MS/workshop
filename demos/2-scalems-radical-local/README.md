## Example 00

Execute a decorated function from a Python module file.

The Python file:
```python
import sys

import scalems


@scalems.app
def main():
    cmd = scalems.executable(argv=['/bin/echo'] + sys.argv[1:], stdout='stdout')

```

### Docker runtime environment
```shell=
docker run --rm --name scalems_test -d scalems/example-complete:v0.0.1
# The MongoDB server needs a few moments to start up.
sleep 3
docker exec -ti -u rp scalems_test bash
. rp-venv/bin/activate
...
docker stop scalems_test
```

### Invocation

Command line invocation of a `scalems` script, using the built-in scalems execution modules.

Trivial local execution:
```shell
python -m scalems.local scalems/examples/basic/echo.py hi there
cat 0*0/stdout
```

RP local:
```shell
python -m scalems.radical --resource=local.localhost --venv $VIRTUAL_ENV --log-level debug scalems/examples/basic/echo.py hi there
```

Remote:

```shell
docker compose -f ~/develop/PycharmProjects/scalems-local/docker/docker-compose.yml exec -ti -u rp login bash
. rp-venv/bin/activate
python -m scalems.radical --resource docker.compute --access ssh --venv /home/rp/rp-venv/ /tmp/scalems_dev/examples/basic/echo.py hi there
 ```


From GitHub Actions test: `python -m scalems.radical --venv=$HOME/testenv --resource=local.github --access=ssh --pilot-option cores=1 --pilot-option gpus=0 examples/basic/echo.py hello world`
