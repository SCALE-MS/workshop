# SCALE-MS workshop material

The git repository for this content is hosted at 
https://github.com/SCALE-MS/workshop

Workshop material includes content originally presented through
https://github.com/kassonlab/gmxapi-tutorials,
derived from the example in Figure 1 of [10.1371/journal.pcbi.1009835](https://dx.plos.org/10.1371/journal.pcbi.1009835)

## Repository Contents

### Sample inputs

Sample input files for these examples have been shared from previous research projects. They are covered by separate copyright and licensing details.

BRER workflow sample inputs: [DOI 10.5281/zenodo.5122931](https://zenodo.org/record/5122931)

FS peptide ([`input_files/fs-peptide/`](input_files/fs-peptide/)):
Sorin and Pande, Biophys J. 2005 Apr; 88(4): 2472–2493; doi:10.1529/biophysj.104.051938 (used with permission).

## Getting started

* Install the required software.
* Get the sample input files.
* Clone this repository or pull a Docker image.

### Install the software

Get the gmxapi 2022 software stack

* GROMACS 2022: https://gitlab.com/gromacs/gromacs/-/archive/release-2022/gromacs-release-2022.tar.gz
* gmxapi 0.3: use `pip install gmxapi` after installing and activating GROMACS 2022

Refer to installation instructions at the respective project websites.
* [gmxapi on GROMACS](https://manual.gromacs.org/current/gmxapi/userguide/install.html), 
* [SCALE-MS Python package](https://scale-ms.readthedocs.io/en/latest/install.html)

Note that `scalems` depends on [RADICAL Pilot](https://radicalpilot.readthedocs.io/en/stable/).
If you use `pip` to install `scalems`, `radical.pilot` and its dependencies will be installed automatically.
Refer to https://scale-ms.readthedocs.io/en/latest/install.html for more information.

### Alternative: Docker

If you prefer to use a containerized installation of the software and examples,
and you are comfortable with Docker,
see the [docker](docker) directory in this repository
or pull `scalems/example-complete` from
[DockerHub](https://hub.docker.com/r/scalems/example-complete).

## Accessing the tutorial material

### From a local Python virtual environment

First, install GROMACS 2022, create a Python virtual environment, and install the `gmxapi` Python package (see above))

0. Clone this repository.
   ```shell
   git clone https://github.com/SCALE-MS/workshop.git
   cd workshop
   ```
1. Install additional tutorial dependencies in the virtual environment, using the provided [requirements.txt](requirements.txt).
    ```shell
    . /path/to/venv/bin/activate
    pip install -r requirements.txt
    ```
2. Install the support package for the workshop.
   ```shell
   pip install .
   ```
3. Refer to the scripts in `examples/`

### From Docker

If you have [Docker](https://www.docker.com/get-started) installed,
you can build an image from the included [Dockerfile](docker/example-complete.dockerfile)
or `docker pull scalems/example-complete`.

See [docker/README.md](docker/README.md) for more information.

### Docker notes
**Warning:**
The `--rm` in the command line above tells Docker to remove the container when you shut down the container.
Any edits you make to the notebook will be lost.
If you want to save your changes,
the best choice is to use the File->Download option from within the notebook.
Alternatively, you could explicitly make a snapshot of the container with
[`docker commit`](https://docs.docker.com/engine/reference/commandline/commit/).
You could run `docker` without the `--rm` option,
but you will need to clean up extra containers manually to keep from filling up your hard disk.

## Caveats (TODOs)

Workflow is not checkpointed. You are advised to use a clean working directory for each script invocation.
