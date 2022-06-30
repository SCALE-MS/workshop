From randowtal test. Ref https://github.com/SCALE-MS/randowtal

# Demo

1. https://github.com/SCALE-MS/randowtal/blob/tmp/am/test_am/brer_worker.py
2. https://github.com/SCALE-MS/randowtal/blob/tmp/am/test_am/brer_master.py
3. https://github.com/SCALE-MS/randowtal/blob/tmp/am/test_am/run_remote.py

# updates

Use GROMACS 2022.2, gmxapi 0.3.x, `$HOME/modules-frontera`, `$WORK/software/gromacs2022`, `$WORK/venv/workshop`

# original notes (needs update)

Clone with `git clone --recursive git@github.com:scalems/randowtal.git`

Update with `git pull --recurse-submodules`

## Contents

Assume the repository is cloned to `$PROJECT`.

`$PROJECT`/ contains some bash SLURM scripts and some Python workflow scripts.

`$PROJECT/external` contains some `git` submodules.

Additional files and directories may be created in the repository by jobs or scripts, but most storage will target `$WORK` or `$SCRATCH`.

`git` submodules include
* `run_brer` Python package
* BRER plugin for GROMACS MD (`brer` Python package)

The build also requires downloads of archives for
* GROMACS 2021 (supporting gmxapi 0.2)
* gmxapi 0.2 (via pip)

## Set up

At least one Python `venv` and at least one GROMACS installation are needed.

`build-frontera.sh` should just work, but should also be fairly self-explanatory on inspection.

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
    *Question: Why doesn't RP get this from the `rp.Context.user_id`?*

### Set up the client-side workflow environment.
Something like:
```
python3 -m pip ~/rp-venv
. ~/rp-venv/bin/activate; pip install --upgrade pip setuptools wheel
git clone git@github.com:SCALE-MS/scale-ms.git
pip install -r scale-ms/requirements-testing.txt
pip install -e scale-ms
git clone git@github.com:SCALE-MS/randowtal.git
```

### Set up the execution environment

On Frontera, the following assumes you did 
```
export PROJECT=$HOME/projects/randowtal && mkdir -p $PROJECT
```
... and that you are me.

Prepare the software stack. We need
* GROMACS 2021.3 (we will use a thread-MPI build)
* gmxapi 0.2.2
* brer 2.0
* run_brer 2.0
* RCT 1.6.8

A usable environment can be achieved as follows.

```
module unload python3
module unload impi
module unload intel
module load gcc
module load impi
module load python3
```

and

```
mkdir $WORK/venv
python3 -m venv $WORK/venv/randowtal
. $WORK/venv/randowtal/bin/activate
pip install --upgrade pip setuptools wheel
pip install scikit-build
MPICC=`which mpicc` pip install mpi4py
```

#### GROMACS

```
wget ftp://ftp.gromacs.org/gromacs/gromacs-2021.3.tar.gz
tar zxvf gromacs-2021.3.tar.gz
mkdir $WORK/software
pushd gromacs-2021.3
  mkdir build
  pushd build
    cmake .. -DCMAKE_INSTALL_PREFIX=$WORK/software/gromacs2021 \
      -DCMAKE_C_COMPILER=`which gcc` \
      -DCMAKE_CXX_COMPILER=`which g++` \
      -DGMX_BUILD_OWN_FFTW=ON \
      -DGMX_THREAD_MPI=ON
    make -j10 install
  popd
popd
```

Oh! And `chmod -R 755 $WORK/software/gromacs2021`.

Now we can all use my installation:

    . /work/02634/eirrgang/frontera/software/gromacs2021/bin/GMXRC

#### gmxapi

`pip install 'gmxapi>=0.2.2'`

#### The workflow

Use the `--recursive` option to get the repositories of some dependencies.

`git clone --recursive git@github.com:SCALE-MS/randowtal.git $PROJECT && cd $PROJECT`


#### brer plugin

```shell
pushd external/brer_plugin
  mkdir build
  pushd build
    gmxapi_DIR=$WORK/software/gromacs2021/share/cmake/gmxapi \
    GROMACS_DIR=$WORK/software/gromacs2021/share/cmake/gromacs \
    cmake ../ \
      -DCMAKE_C_COMPILER=`which gcc` \
      -DCMAKE_CXX_COMPILER=`which g++` \
      -DGMXPLUGIN_INSTALL_PATH=$(echo $VIRTUAL_ENV/lib/python*/site-packages/)
    make -j10 install
  popd
popd
```

#### run_brer

`(cd external/run_brer && python setup.py install)`

#### share

`chmod -R 755 /work/02634/eirrgang/frontera/venv/`

Now we can all use my venv.

## Inputs

To start with, we can just get the input TPR file and the pair distance distribution data from static locations on Frontera:
* `/home1/02634/eirrgang/projects/lccf_gmx2021-patched/input/hiv-deer/nosugar_ver116.tpr`
* `/home1/02634/eirrgang/projects/lccf_gmx2021-patched/input/hiv-deer/pair_dist.json`

## Example

Originally, our lccf jobs used solely mpi4py ensemble management in gmxapi, exhibiting the following call hierarchy.

`job_normal.sh` -> `workflow.py` -> `import run_brer; ...`

We developed a RP-wrapped version of the workflow, architected as follows.

**Client side:** `clientdir/run_remote.sh` -> `rp-ensemble.py` -> `import radical.pilot as rp`

**Execution side:** rp.Task: `brer_runner.py` -> `import run_brer; ...`

### mpi4py gmxapi ensemble management

`job_normal.sh` illustrates a (non-RP) gmxapi brer job, which requires missing sbatch options to be provided on the command line.
Example:

    for N in 4 16 64 128 256; do sbatch -J brer2021_$N -N $N -n $N job_normal.sh ; done

### RADICAL Pilot ensemble management

* When creating a `rp.Context`, set `context.user_id = 'rpilot'`
* From the shell on the VM, start an ssh-agent, and add the key.
  `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_rsa`
* Note the paths on the remote machine (frontera).
* Launch `tmux`! RP does not provide a way to disconnect the client from the Pilot session.
* Run the script to launch an rp Pilot as `rpilot@frontera`.
  See the `run_remote.sh` scripts in subdirectories.
