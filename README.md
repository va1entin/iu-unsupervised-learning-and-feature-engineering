# iu-unsupervised-learning-and-feature-engineering

This is the code for a case study I wrote for the IU International University of Applied Sciences module "Unsupervised Learning and Feature Engineering" with module code `DLBDSMLUSL01`.

In this case study, I process an Arxiv metadata set using both LDA and BERTopic topic models, each on just paper titles and on a concatenation of titles and abstracts to determine the performance of each technique and how it changes with a denser input corpus.

I used a VM on Azure deployed with Terraform for the necessary computations so this README instructs you on how to do that.

## Install locally required packages
You'll need the Azure CLI and Terraform to deploy the VM for our computations.

[Installation info for Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)

[Installation info for Terraform](https://developer.hashicorp.com/terraform/install)

## Get Azure access
Once both are installed, you need to make sure that you have an active local login for your Azure account. This command should show a list of your Azure subscriptions. Also, make sure that the correct subscription is active (has `"isDefault": True` set) such that the resources get billed correctly.
```bash
az account list
```

If you don't have an active login, use the following command to login. It'll give you a device code to enter on `https://login.microsoft.com/device`.
Once you've entered the code and logged into your account, the CLI should print your Azure subscription(s) and you can choose which one should be the active one to deploy resources to if you have multiple available.
```bash
az login --use-device-code
```

You can change your active subscription any time using the following command where `mysubscription` is the name of your desired active subscription.
```bash
az account set --subscription mysubscription
```

## Deployment of resources with Terraform
Now, make sure that you are in the root folder of this repository and initialize it for Terraform usage
```bash
terraform init
```

To deploy the resources in the next step, you'll need your SSH key ready. It'll be used to login to the VM later. It's usually located at `~/.ssh` on *nix systems and, by default, named `id_<algorithm>.pub`. Usually `rsa` or `ed25519` are used as encryption algorithm, so your public key will most likely be named `id_rsa.pub` or `id_ed25519.pub`. Copy the content of the file to the clipboard.

```bash
cat ~/.ssh/id_ed25519.pub # Copy the contents to clipboard
```

Now you can deploy the resources!

You can optionally just display what _would_ be deployed by running
```bash
terraform plan -out plan.tf
```

and then apply that plan using
```bash
terraform apply plan.tf
```

or deploy directly without a separate plan step. Don't worry, you'll still be shown the changes and prompted to confirm!

```bash
terraform apply
```

Now the VM and it's accompanying resources will be created. By default, the machine is configured to only allow connections from your current IP, which is obtained from `https://api.ipify.org` when you run plan or apply without providing a plan file. Once creation is finished, Terraform will display a SSH command that should give you direct access to the machine upon execution.

Due to some issues with either Azure itself or the azurerm Terraform provider the (un)deployment works about 9/10 for me but fails in that last 1/10 cases. It appears that Azure sometimes hits internal race conditions when attaching the network interface to the VM in particular.

As this is not a persistent issue and sometimes many deployments work without any problems, I'm very sure it's an upstream issue we just need to navigate around when it happens, unfortunately.

In the case of an incomplete deployment please `terraform destroy` it, manually via the portal if needed and try again. Thank you <3

## Installation of required packages

All needed packages will be automatically installed at VM startup by the `vm-startup.sh` script. Installing Python packages in particular takes a while so please **wait for a file `/home/azureuser/setup_finished` to appear on the VM after deploying it before you run any notebooks or code from this repo**.

## BERTopic patch

The startup script applies a small patch to BERTopic as it contains two minor bugs in its `topics_over_time` function as of version `0.17.4`.


1. It tries to see if there are topics stored on the `topic_model` object itself as `self._topics` and use those if no `topics` parameter was provided; this doesn't work properly so I just force it to use the topics explicitly provided.
2. It calls `Pandas.to_datetime` with a parameter `infer_datetime_format` which was [removed in Pandas 3.0 released in January 2026](https://github.com/pandas-dev/pandas/pull/48621) so I remove it as the function works nonetheless.

## Get Arxiv dataset

Download version 282 of the Arxiv dataset [from Kaggle](https://www.kaggle.com/datasets/Cornell-University/arxiv/versions/282) and push it to the VM path `/home/azureuser/iu-unsupervised-learning-and-feature-engineering/arxiv-metadata-oai-snapshot-v282.json` like so:

```bash
scp arxiv-metadata-oai-snapshot.json azureuser@<IP>:iu-unsupervised-learning-and-feature-engineering/arxiv-metadata-oai-snapshot-v282.json
```

## Open remote VS code session

This is my preferred working environment - you're of course welcome to do it your own way!

1. Open [VS Code](https://code.visualstudio.com/download) and install the `Remote - SSH` [extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh).
2. Press `Ctrl+Shift+P` and type `Connect to Host`, then select `Remote-SSH: Connect to Host...` by highlighting it and pressing Enter
3. Type `azureuser@<IP of your VM>` and hit Enter
4. VS Code should connect to your VM and take a moment to install its server components
5. Open the folder `iu-unsupervised-learning-and-feature-engineering` and then the notebook you want to run, you can "Trust" the folder when prompted
6. When running a notebook, VS Code will ask you in which environment to do so. Select `Python environments` and then `iu-unsupervised-learning-and-feature-engineering (Python 3.13.5)`. When prompted whether to install the required/recommended extensions, just hit Enter for VS Code to install needed components remotely.

## Embeddings generation

BERTopic requires the input dataset to be embedded into vector space to process it further. This is very slow on CPU but fast on GPU. Unfortunately, it's currently quite difficult to obtain GPU resources in Azure unless you're a corporate customer. 

You can of course compute the embeddings on CPU, in fact the BERTopic notebook will detect automatically if there are any CUDA devices and, if not, use a multi process CPU pool instead but if you have a GPU somewhere, you can download the preprocessed data for BERTopic, generate embeddings locally and upload them back to the VM.

The preprocessed data artifact for BERTopic is saved to `/home/azureuser/iu-unsupervised-learning-and-feature-engineering/artifacts/Preprocessing/arxiv-metadata-cleaned_BERTopic.parquet` by the preprocessing pipeline `2_Preprocessing.ipynb`. You'll need to download the entire folder for embeddings generation.

Use the variable `load_embeddings` in the first code cell to tell the BERTopic notebook tp either compute new or load existing embeddings.

Embeddings are saved to/expected at `/home/azureuser/iu-unsupervised-learning-and-feature-engineering/artifacts/BERTopic/bertopic-<corpus type>-<corpus row count>-embeddings.npy` where `corpus type` is either `title` or `concat` and `corpus row count` should be `1632186` if you use the Preprocessing pipeline and version `282` of the dataset as instructed.

## Removal of resources with Terraform
Once you're done using the machine and extracted all desired artifacts, you can remove the VM.

Again, make sure to run this in the root folder of this repository on your machine. Terraform will print which resources it'll remove and you have to confirm by typing 'yes'.

**Don't forget to destroy or at least deallocate unused resources as they'll keep incurring charges!**

```bash
terraform destroy
```

### VM deallocation
If you want to keep the machine around instead of destroying it but save costs while it's not in use, you can stop the VM and dellocate its hardware resources.

First, shut the VM down by running `sudo poweroff` in a SSH session.

Now, even with the VM shut down, **Azure will keep billing you for the hardware resources the machine uses until you _deallocate_ it**.

Open `https://portal.azure.com`, click on "Resource Groups" in the left pane and locate the resource group `iu-usl-fe`. Open the resource group and look for a virtual machine resource named `iu-usl-fe-vm`, then open it. The machine should be listed with `Status: Stopped`. If not, refresh after a few seconds as the shutdown you executed earlier might still be in progress.

Click on the `Stop` button and confirm the prompt to deallocate underlying resources. When you start the machine next time, resources will automatically be allocated again.

**Note, that you'll continue to be billed for other resources like the public IP even when the VM is deallocated. These costs are marginal in comparison to the VM, though.**

**You can inspect costs by opening the resource group and clicking on "Cost Management" -> "Cost analysis" in the resource group's pane.**
