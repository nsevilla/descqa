# Massive Black 2 galaxy catalog class

from GalaxyCatalogInterface import GalaxyCatalog
import numpy as np
from astropy.table import Table
import astropy.units as u
import astropy.cosmology

class MB2GalaxyCatalog(GalaxyCatalog):
    """
    Massive Black 2 galaxy catalog class.
    """

    def __init__(self, fn=None):
        self.type_ext =   'MB2'
        self.filters  = {
                          'zlo':                   True,
                          'zhi':                   True
                        }
        self.h          = 0.702
        self.cosmology = astropy.cosmology.FlatLambdaCDM(H0=self.h*100.0, Om0 = 0.275)
        self.quantities = {
                             'halo_id':               self._get_stored_property,
                             'parent_halo_id':        self._get_stored_property,
                             'redshift':              self._get_stored_property,
                             'positionX':             self._get_derived_property,  # Position returned in Mpc, stored in kpc/h
                             'positionY':             self._get_derived_property,
                             'positionZ':             self._get_derived_property,
                             'velocityX':             self._get_stored_property,   # Velocity returned in km/sec
                             'velocityY':             self._get_stored_property,   # Velocity returned in km/sec
                             'velocityZ':             self._get_stored_property,   # Velocity returned in km/sec
                             'mass':                  self._get_derived_property,  # Masses returned in Msun but stored in 1e10 Msun/h
                             'stellar_mass':          self._get_derived_property,
                             'gas_mass':              self._get_stored_property,
                             'sfr':                   self._get_stored_property,
                             'SDSS_u:observed:':      self._get_derived_property,
                             'SDSS_g:observed:':      self._get_derived_property,
                             'SDSS_r:observed:':      self._get_derived_property,
                             'SDSS_i:observed:':      self._get_derived_property,
                             'SDSS_z:observed:':      self._get_derived_property,
                           }

        self.derived      = {
                             'mass':            (('mass',), (1.e10 / self.h,), self._multiply),
                             'stellar_mass':    (('stellar_mass',), (1.e10 / self.h,), self._multiply),
                             'positionX':       (('x',), (1.e-3 / self.h,), self._multiply), # Position stored in kpc/h
                             'positionY':       (('y',), (1.e-3 / self.h,), self._multiply),
                             'positionZ':       (('z',), (1.e-3 / self.h,), self._multiply),
                             'SDSS_u:observed:': (('SDSS_u:rest:', 'redshift'), (), self._add_distance_modulus),
                             'SDSS_g:observed:': (('SDSS_g:rest:', 'redshift'), (), self._add_distance_modulus),
                             'SDSS_r:observed:': (('SDSS_r:rest:', 'redshift'), (), self._add_distance_modulus),
                             'SDSS_i:observed:': (('SDSS_i:rest:', 'redshift'), (), self._add_distance_modulus),
                             'SDSS_z:observed:': (('SDSS_z:rest:', 'redshift'), (), self._add_distance_modulus),
                            }
        self.Ngals        = 0
        self.sky_area     = 4.*np.pi*u.sr   # all sky by default
        self.lightcone    = False
        self.box_size     = 100.0 / self.h
        return GalaxyCatalog.__init__(self, fn)

    def load(self, fn):
        """
        Given a catalog path, attempt to read the catalog and set up its
        internal data structures.
        """
        self.catalog = Table.read(fn, path='data')
        self.Ngals = len(self.catalog)
        self.redshift = self.catalog['redshift'][0]

        return self

    def _construct_mask(self, filters):
        """
        Given a dictionary of filter constraints, construct a mask array
        for use in filtering the catalog.
        """
        if type(filters) is not dict:
            raise TypeError("construct_mask: filters must be given as dict")
        mask = np.ones((self.Ngals), dtype=np.bool_)
        mask = mask & (np.isfinite(self.catalog['x'])) # filter out NaN positions from catalog
        mask = mask & (np.isfinite(self.catalog['y']))
        mask = mask & (np.isfinite(self.catalog['z']))
        for filter_name in filters.keys():
            if filter_name == 'zlo':
                mask = mask & (filters[filter_name] < self.catalog['redshift'])
            elif filter_name == 'zhi':
                mask = mask & (filters[filter_name] > self.catalog['redshift'])
        return mask

    def _get_stored_property(self, quantity, filters):
        """
        Return the requested property of galaxies in the catalog as a NumPy
        array. This is for properties that are explicitly stored in the
        catalog.
        """
        filter_mask = self._construct_mask(filters)
        return self.catalog[quantity][np.where(filter_mask)].data

    def _get_derived_property(self, quantity, filters):
        """
        Return a derived halo property. These properties aren't stored
        in the catalog but can be computed from properties that are via
        a simple function call.
        """
        filter_mask = self._construct_mask(filters)
        arrays_required, scalars, func = self.derived[quantity]
        return func([self.catalog[name][np.where(filter_mask)].data for name in arrays_required], scalars)

    # Functions for computing derived values
    def _translate(self, propList):
        """
        Translation routine -- a passthrough that accomplishes mapping of
        derived quantity names to stored quantity names via the derived
        property function mechanism.
        """
        return propList

    def _multiply(self, array_tuple, scalar_tuple):
        """
        Multiplication routine -- derived quantity is equal to a stored
        quantity times some factor. Additional args for the derived quantity
        routines are passed in as a tuple, so extract the factor first.
        """
        return array_tuple[0] * scalar_tuple[0]


    def _add_distance_modulus(self, array_tuple, scalar_tuple):
        return array_tuple[0] + self.cosmology.distmod(array_tuple[1]).value
