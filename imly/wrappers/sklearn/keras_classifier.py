from numpy.random import seed
seed(3)
from tensorflow import set_random_seed
set_random_seed(3)

from keras.wrappers.scikit_learn import KerasClassifier
from optimizers.tune.tune import get_best_model
import pickle, onnxmltools
import numpy as np


class SklearnKerasClassifier(KerasClassifier):
        def __init__(self, build_fn, **kwargs):
            super(KerasClassifier, self).__init__(build_fn=build_fn)
            self.primal = kwargs['primal']
            self.params = kwargs['params']

        def fit(self, x_train, y_train, **kwargs):
            print('Keras classifier chosen')
            kwargs.setdefault('params', self.params)
            # This params is to hold the values passed by the user
            kwargs.setdefault('space', False)
            primal_model = self.primal
            primal_model.fit(x_train, y_train)
            y_pred = primal_model.predict(x_train)
            primal_data = {
                'y_pred': y_pred,
                'model_name': primal_model.__class__.__name__
            }
            hyperopt_space = kwargs['space']
            self.params.update(kwargs['params'])
            # Merging params passed by user(if any) to the default params

            '''
            Note -
            This is to update the 'classes_' variable used in keras_regressor.
            'classes_' variable is used by the score function of keras_regressor.
            An alternate option would be to create our own score function.
            Move this to a wrapper score.
            '''

            y_train = np.array(y_train)
            if len(y_train.shape) == 2 and y_train.shape[1] > 1:
                self.classes_ = np.arange(y_train.shape[1])
            elif (len(y_train.shape) == 2 and y_train.shape[1] == 1) or len(y_train.shape) == 1:
                self.classes_ = np.unique(y_train)
                y_train = np.searchsorted(self.classes_, y_train)
            else:
                raise ValueError('Invalid shape for y_train: ' + str(y_train.shape))

            if (kwargs['params']!=self.params or kwargs['space']):
                ## Search for best model using Tune ##
                self.model = get_best_model(x_train, y_train,
                                            primal_data=primal_data,
                                            params=self.params, space=hyperopt_space)
                self.model.fit(x_train, y_train, epochs=200,
                               batch_size=30, verbose=0)
            else:
                # This else case is triggred if the user opts out of optimization
                mapping_instance = self.build_fn
                # build_fn passed from dope holds the class instance with param_name and fn_name.
                # Hence, mapping variables are already available.
                self.model = mapping_instance.__call__(x_train=x_train, params=kwargs['params'])
                self.model.fit(x_train, y_pred)

            # TODO
            # Add a validation to check if the user has opted for 
            # optimization. If not, call 'fit' from KerasClassifier.

        def save(self, using='dnn'):
            if using == 'sklearn':
                filename = 'scikit_model'
                pickle.dump(self.model, open(filename, 'wb'))
            else:
                onnx_model = onnxmltools.convert_keras(self.model)
                return onnx_model
