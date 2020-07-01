import sys
import subprocess
import git
import argparse
import random


def parse_opts():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ignore", action="store_true",
                        help="Ignore committing code and data.")
    parser.add_argument("-l", "--local", action="store_true",
                        help="Train on the local machine.")
    parser.add_argument("-c", "--cluster", type=str,
                        help="Train on a cluster. Specify the IP address.")
    args = parser.parse_args()
    print(args)
    return args


class Session:
    # TODO: Need to fix this path correctly
    def __init__(self, args, path, model=None, batch_gen=None,
                 hyperparam=None):
        '''
        If model is a single object and hyperparam is a dictionary with only 
        one set of value, then we are training a single model for a given hyperparameter

        If model is a list of strings corresponding to the various 
        sklearn models, then we are training multiple models on the same 
        data. In that case, hyperparameter will be be dictionary where the key will be the model name
        and the value will be a dictionary of parameters


        If model is a single object and hyperparam is a dictionary with a list or tuple  
        of values, then we are training with hyperparameter tuning (Ray Tune)

        If num_replicas is specified, then we are going to do data parallelization (Ray SGD)

        We will need a method to start the cluster and stop the cluster using __enter__ and __exit__

        We will have a method that will create a docker container from the successful model (Ray Serve)

        '''

        self.__check_git_initialized(path)
        self.__check_dvc_initialized()

        if not args.ignore:
            # use echo $( git status --porcelain | grep .; )
            # to check if there are any commits yet to be made.
            print('Please ensure that all changes to git and dvc ' +
                  'are commited. First commit changes to dvc and then ' +
                  'commit changes to git. If you wish to ignore changes ' +
                  'and proceed further, use the -i flag.')
            sys.exit(0)

        self.model = model
        self.batch_gen = batch_gen
        self.hyperparam = hyperparam
        print('finished')

    def __check_git_initialized(self, path):
        # check if this folder is a git repo. if not throw exception and stop
        try:
            repo = git.Repo(path)
            _ = repo.git_dir
        except git.exc.InvalidGitRepositoryError:
            print('Please create a git repo by running "git init" and ' +
                  'then run the code again.')
            sys.exit(0)

    def __check_dvc_initialized(self):
        try:
            subprocess.check_call(['dvc', 'init'],  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass  # dvc is already initalized. So nothing else to be done.add


class Data:
    def __init__(self, train_x, train_y=None, test_x=None, test_y=None, split=0.2):
        self.train_x = train_x
        self.train_y = train_y
        self.test_x = test_x
        self.test_y = test_y
        self.split = split

        # train_y is None, implies unsupervised learning

        # No test data passed implies, we need to split and get test
        # data from train_x
        if test_x is None and test_y is None:
            pass

    def generator(self, train=True, batch_size=32):
        count = 0
        array_length = self.train_x.shape[0] if train else self.test_x.shape[0]
        while count < array_length/batch_size:
            randstart = random.randint(0, array_length-batch_size-1)
            count += 1
            if train:
                if self.train_y is None:
                    yield (self.train_x[randstart:randstart+batchsize],)
                else:
                    yield (self.train_x[randstart:randstart+batchsize],
                           self.train_y[randstart:randstart+batchsize])
            else:
                if self.test_y is None:
                    yield (self.test_x[randstart:randstart+batchsize],)
                else:
                    yield (self.test_x[randstart:randstart+batchsize],
                           self.test_y[randstart:randstart+batchsize])


class Model:
    def __init__(self, model, hyper_param):
        self.model = model
        self.hyper_param = hyper_param