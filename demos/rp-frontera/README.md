# Use the scalems.radical backend on Frontera
## Set up

* frontera account
* rpilot@frontera access
* proxy login server access
* frontera python environment
* job parameters

### Get access

1. Contact Matteo for an account on the VM at `95.217.193.116` to get a shell account and a MongoDB database.
1. Generate an ssh key pair (`ssh username@95.217.193.116 ssh-keygen`)
1. Ask Matteo/Andre to add the public key to `authorized_keys` for `rpilot@frontera.tacc.utexas.edu`.
1. Add `rpilot` to the Frontera allocation. Make sure that `rpilot@frontera` is a member of an appropriate group to get access to the software and data used by the scripts. *We're using group `G-821136`*
1. Let `rpilot` be the default user id when connecting from the VM to frontera. Add this to your ~/.ssh/config:
    ```
    host frontera.tacc.utexas.edu
       user = rpilot
    ```

### Set up the client-side workflow environment.
Something like:
```shell
python3 -m pip ~/venv/workshop
. ~/venv/workshop/bin/activate; pip install --upgrade pip setuptools wheel
git clone git@github.com:SCALE-MS/scale-ms.git
pip install -r scale-ms/requirements-testing.txt
pip install -e scale-ms
```

### Set up the execution environment

On Frontera, the following assumes you did 
```shell
export PROJECT=$HOME/projects/scalems-workshop && mkdir -p $PROJECT
```
... and that you are me.

Prepare the software stack. We need
* GROMACS 2022.2 (we will use a thread-MPI build)
* gmxapi 0.3.2
* RCT 1.14.0

A usable environment can be achieved as follows.

```shell
module unload python3
module unload impi
module unload intel
module load gcc
module load impi
module load python3
```

and

```shell
mkdir $WORK/venv
python3 -m venv --system-site-packages $WORK/venv/workshop
. $WORK/venv/workshop/bin/activate
pip install --upgrade pip setuptools wheel
MPICC=`which mpicc` pip install mpi4py
```

Make sure `rpilot` can use it:
```shell
chmod -R 755 $WORK/venv
```
### RADICAL Pilot ensemble management

* When creating a `rp.Context`, set `context.user_id = 'rpilot'`
* From the shell on the VM, start an ssh-agent, and add the key.
  `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_rsa`
* Note the paths on the remote machine (frontera).
* Launch `tmux`! RP does not provide a way to disconnect the client from the Pilot session.

## Example 00-alt

**WORK IN PROGRESS**

```shell
python -m scalems.radical \
    --venv /work2/02634/eirrgang/frontera/venv/workshop \
    --resource tacc.frontera \
    --log-level DEBUG \
    --pilot-option project=MCB20024 \
    --pilot-option runtime=2 \
    --pilot-option cores=1 \
    --pilot-option queue=small \
    echo.py hi there
```

### TODO

Programmatic handling of `rp.Context` details.

```python
if getattr(self.pilot_description(), 'resource', 'localhost') == 'tacc.frontera':
            context = rp.Context('ssh')
            context.user_id = 'rpilot'
            session.add_context(context)
```

scalems parser support for pre-execution (environment preparation) shell snippets.

Example job configurables:

python ../rp-ensemble.py \
  --workers $SIZE \
  --threads 56 \
  --ensemble-size $SIZE \
  --resource tacc.frontera \
  --input $INPUT \
  --pairs $PAIRS \
  --walltime $HOURS \
  --workdir /scratch1/02634/eirrgang/randowtal/brer-rp-gmx2021-$SIZE \
  --pre ". /home1/02634/eirrgang/projects/randowtal/modules.frontera" \
  --pre "umask 007" \
  --task /home1/02634/eirrgang/projects/randowtal/brer_runner.py \
  --python /work/02634/eirrgang/frontera/venv/randowtal/bin/python \
  --project MCB20024
