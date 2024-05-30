import os
import json

root = os.path.abspath(os.sep)


def getDocketSecrets(
    name, secretsPath=os.path.abspath(os.path.join(os.sep, "run", "secrets"))
):
    """This function fetches a docker secret

    :param name: the name of the docker secret
    :param secretsPath: the directory where the secrets are stored
    :returns: docker secret
    :raises ValueError: if the secrets cannot be parsed
    :raises IOError: if [secretsPath] cannot be opened
    :raises KeyError: if [name] nof found in the secrets
    """

    secretsFile = os.listdir(secretsPath)[0]
    secretsFilePath = os.path.join(secretsPath, secretsFile)

    with open(secretsFilePath) as f:
        secrets = json.load(f)
    return secrets[name]
