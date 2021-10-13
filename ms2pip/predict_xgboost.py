"""Get predictions directly from XGBoost model, within ms2pip framework."""

from genericpath import isfile
from itertools import islice
import os
import urllib.request


import numpy as np
import xgboost as xgb
import hashlib

from ms2pip.ms2pipC import AMINO_ACID_IDS, ms2pip_pyx
from ms2pip.exceptions import (
    InvalidModificationFormattingError,
    InvalidXGBoostModelError,
    UnknownModificationError,
    UnknownFragmentationMethodError,
)


def process_peptides_xgb(peprec, model_params, ptm_ids, num_cpu=1):
    """Get predictions for peptides directly from XGBoost model."""
    feature_vectors, mzs = _get_ms2pip_data_for_xgb(peprec, model_params, ptm_ids)
    feature_vectors = xgb.DMatrix(feature_vectors)

    num_ions = (peprec["peptide"].str.len() - 1).to_list()
    peptide_lengths = peprec["peptide"].str.len().to_list()
    charges = peprec["charge"].to_list()
    spec_ids = peprec["spec_id"].to_list()

    preds_list = []
    for ion_type, model_file in model_params["xgboost_model_files"].items():
        # Check if  xgb models are present, if not dowload them
        if not check_model_presence(model_file):
            download_model(model=model_file)

        # Get predictions from XGBoost model
        bst = xgb.Booster({"nthread": num_cpu})
        bst.load_model(model_file)
        preds = bst.predict(feature_vectors)

        # Reshape into arrays for each peptide
        preds = _split_list_by_lengths(preds, num_ions)
        if ion_type in ["x", "y", "z"]:
            preds = [np.array(x[::-1], dtype=np.float32) for x in preds]
        elif ion_type in ["a", "b", "c"]:
            preds = [np.array(x, dtype=np.float32) for x in preds]
        else:
            raise ValueError(f"Unsupported ion_type: {ion_type}")
        preds_list.append(preds)

    predictions = [list(t) for t in zip(*preds_list)]

    # List of objects with `get` method is expected, use spoofer class
    return [
        _MultiprocessingResultSpoofer(
            (mzs, predictions, None, peptide_lengths, charges, spec_ids)
        )
    ]


def _get_ms2pip_data_for_xgb(peprec, model_params, ptm_ids):
    """Get feature vectors and mz values for all peptides in self.data."""
    peaks_version = model_params["peaks_version"]

    vector_list = []
    mz_list = []
    for row in peprec.to_dict(orient="records"):

        peptide = np.array(
            [0] + [AMINO_ACID_IDS[x] for x in row["peptide"].replace("L", "I")] + [0],
            dtype=np.uint16,
        )
        modpeptide = apply_mods(peptide, row["modifications"], ptm_ids)
        charge = row["charge"]

        vector_list.append(
            np.array(
                ms2pip_pyx.get_vector(peptide, modpeptide, charge), dtype=np.uint16
            )
        )
        mzs = ms2pip_pyx.get_mzs(modpeptide, peaks_version)
        mz_list.append([np.array(m, dtype=np.float32) for m in mzs])

    feature_vectors = np.vstack(vector_list)

    return feature_vectors, mz_list


def _split_list_by_lengths(list_in, lengths):
    list_in = iter(list_in)
    return [list(islice(list_in, elem)) for elem in lengths]


class _MultiprocessingResultSpoofer:
    """Spoof result structure of multiprocessing, for direct XGB predictions."""

    def __init__(self, contents):
        self.contents = contents

    def get(self):
        return self.contents


def apply_mods(peptide, mods, PTMmap):
    """
    Takes a peptide sequence and a set of modifications. Returns the modified
    version of the peptide sequence, c- and n-term modifications. This modified
    version are hard coded in ms2pipfeatures_c.c for now.
    """
    modpeptide = np.array(peptide[:], dtype=np.uint16)

    if mods != "-":
        l = mods.split("|")
        if len(l) % 2 != 0:
            raise InvalidModificationFormattingError(mods)
        for i in range(0, len(l), 2):
            tl = l[i + 1]
            if tl in PTMmap:
                modpeptide[int(l[i])] = PTMmap[tl]
            else:
                raise UnknownModificationError(tl)

    return modpeptide


def check_model_presence(model):
    """ Check whether xgboost model is downloaded"""

    home = os.path.expanduser("~")
    if not os.path.isdir(os.path.join(home, ".ms2pip")):
        return False
    elif not os.path.isfile(os.path.join(home, ".ms2pip", model)):
        return False
    elif check_model_integrity(os.path.join(home, ".ms2pip", model)):
        return True
    else:
        raise UnknownFragmentationMethodError()


def download_model(model):
    """ Download the xgboost model to user/.ms2pip path"""

    home = os.path.expanduser("~")
    if not os.path.isdir(os.path.join(home, ".ms2pip")):
        os.mkdir(os.path.join(home, ".ms2pip"))

    dowloadpath = os.path.join(home, ".ms2pip", model)
    urllib.request.urlretrieve("modelfilepath", dowloadpath)
    check_model_integrity(dowloadpath)


def check_model_integrity(filename):
    """Check that models are correctly downloaded"""

    MODEL_hashes = {
        "model_20210316_Immuno_HCD_B.xgboost": "977466d378de2e89c6ae15b4de8f07800d17a7b7",
        "model_20210316_Immuno_HCD_Y.xgboost": "71948e1b9d6c69cb69b9baf84d361a9f80986fea",
        "model_20210416_HCD2021_B.xgboost": "c086c599f618b199bbb36e2411701fb2866b24c8",
        "model_20210416_HCD2021_Y.xgboost": "22a5a137e29e69fa6d4320ed7d701b61cbdc4fcf",
    }
    model = filename.rsplit("/", 1)[1]
    sha1_hash = hashlib.sha1()
    with open(filename, "rb") as modelfile:
        while True:
            chunk = f.read(16 * 1024)
            if not chunk:
                break
            sha1_hash.update(chunk)
    if sha1_hash.hexdigest() != MODEL_hashes[model]:
        raise InvalidXGBoostModelError()
    else:
        return True
