from __future__ import division
import numpy as np
from scipy.linalg.blas import dgemm


class PCA(object):
    r"""
    Principal Component Analysis (PCA) by Eigenvalue Decomposition of the
    data's scatter matrix.

    This implementation uses the scipy.linalg.eig implementation of
    eigenvalue decomposition. Similar to Scikit-Learn PCA implementation,
    it only works for dense arrays, however, this one should scale better to
    large dimensional data.

    The class interface augments the one defined by Scikit-Learn PCA class.

    Parameters
    -----------
    n_components : int or None
        Number of components to be retained.
        if n_components is not set all components

    whiten : bool, optional
        When True (False by default) transforms the `components_` to ensure
        that they covariance is the identity matrix.

    center : bool, optional
        When True (True by default) PCA is performed after mean centering the
        data

    bias: bool, optional
        When True (False by default) a biased estimator of the covariance
        matrix is used, i.e.:

            \frac{1}{N} \sum_i^N \mathbf{x}_i \mathbf{x}_i^T

        instead of default:

            \frac{1}{N-1} \sum_i^N \mathbf{x}_i \mathbf{x}_i^T
    """

    def __init__(self, n_components=None, whiten=False,
                 center=True, bias=False):
        self.n_components_ = n_components
        self.whiten = whiten
        self.center = center
        self.bias = bias

    def fit(self, X):
        r"""
        Apply PCA on the data matrix X

        Parameters
        ----------
        x : (n_samples, n_features) ndarray
            Training data

        Returns
        -------
        self : object
            Returns the instance itself.
        """
        self._fit(X)
        return self

    def _fit(self, X):
        r"""
        Apply PCA on the data matrix X

        Parameters
        ----------
        x : (n_samples, n_features) ndarray
            Training data

        Returns
        -------
        eigenvectors : (n_components, n_features) ndarray
        eigenvalues : (n_components,) ndarray
        """
        n_samples, n_features = X.shape

        if self.bias:
            N = n_samples
        else:
            N = n_samples - 1

        if self.center:
            # center data
            self.mean_ = np.mean(X, axis=0)
            X -= self.mean_
        else:
            self.mean_ = np.zeros(n_features)

        if n_features < n_samples:
            # compute covariance matrix
            # S:  n_features  x  n_features
            S = dgemm(alpha=1.0, a=X.T, b=X.T, trans_b=True) / N

            # perform eigenvalue decomposition
            # eigenvectors:  n_features x  n_features
            # eigenvalues:   n_features
            eigenvectors, eigenvalues = _eigenvalue_decomposition(S)

            if self.whiten:
                # whiten eigenvectors
                eigenvectors *= eigenvalues ** -0.5

        else:
            # n_features > n_samples
            # compute covariance matrix
            # S:  n_samples  x  n_samples
            S = dgemm(alpha=1.0, a=X.T, b=X.T, trans_a=True) / N

            # perform eigenvalue decomposition
            # eigenvectors:  n_samples  x  n_samples
            # eigenvalues:   n_samples
            eigenvectors, eigenvalues = _eigenvalue_decomposition(S)

            aux = 2
            if self.whiten:
                # will cause eigenvectors to be whiten
                aux = 1

            # compute final eigenvectors
            # eigenvectors:  n_samples  x  n_features
            w = (N * eigenvalues) ** (-1 / aux)
            eigenvectors = w * dgemm(alpha=1.0, a=X.T, b=eigenvectors.T,
                                     trans_b=True)

        if self.n_components_ is None:
            # set number of components to number of recovered eigenvalues
            self.n_components_ = eigenvalues.shape[0]

        if self.n_components_ < np.min((n_samples, n_features)):
            # noise variance equals average variance of discarded components
            self.noise_variance_ = eigenvalues[self.n_components_:].mean()
        else:
            # if all components are kept, noise variance equals 0
            self.noise_variance_ = 0.

        # transpose eigenvectors
        # eigenvectors:  n_samples  x  n_features
        eigenvectors = eigenvectors.T

        # keep appropriate number of components
        self.components_ = eigenvectors[:self.n_components_, :]
        self.explained_variance_ = eigenvalues[:self.n_components_]
        self.explained_variance_ratio_ = (self.explained_variance_ /
                                          eigenvalues.sum())

        return eigenvectors, eigenvalues

    def transform(self, X):
        r"""
        Apply the dimensionality reduction on X.

        Parameters
        ----------
        X : (n_samples, n_features) ndarray

        Returns
        -------
        Z: (n_samples, n_components) ndarray

        """
        X = X - self.mean_
        Z = dgemm(alpha=1.0, a=X.T, b=self.components_.T, trans_a=True)
        return Z

    def inverse_transform(self, Z):
        r"""
        Parameters
        ----------
        Z : (n_samples, n_components) ndarray

        Returns
        -------
        X: (n_samples, n_features) ndarray

        Notes
        -----
        If whitening is used, inverse_transform does not perform the
        exact inverse operation of transform.
        """
        X = dgemm(alpha=1.0, a=Z.T, b=self.components_.T,
                  trans_a=True, trans_b=True)
        X = X + self.mean_
        return X


def _eigenvalue_decomposition(S, eps=10**-10):
    r"""

    Parameters
    ----------
    S : (N, N)  ndarray
        Covariance/Scatter matrix

    Returns
    -------
    pos_eigenvectors: (N, p) ndarray
    pos_eigenvalues: (p,) ndarray
    """
    # compute eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eig(S)
    # sort eigenvalues from largest to smallest
    index = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[index]
    eigenvectors = eigenvectors[:, index]

    # set tolerance limit
    limit = np.max(np.abs(eigenvalues)) * eps

    # select positive eigenvalues
    pos_index = eigenvalues > 0
    pos_eigenvalues = eigenvalues[pos_index]
    pos_eigenvectors = eigenvectors[:, pos_index]
    # check they are within the expected tolerance
    index = pos_eigenvalues > limit
    pos_eigenvalues = pos_eigenvalues[index]
    pos_eigenvectors = pos_eigenvectors[:, index]

    return pos_eigenvectors, pos_eigenvalues