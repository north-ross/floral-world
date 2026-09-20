import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import unittest.mock
from zipfile import ZipFile

import pandas as pd

LOADER = Path(__file__).resolve().parents[1] / "src/data/family-area-sr.json.py"
spec = importlib.util.spec_from_file_location("wcvp_loader", LOADER)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class RichnessTests(unittest.TestCase):
    def setUp(self):
        self.names = pd.DataFrame([
            ["1", "Accepted", "Species", "Ericaceae", "Temperate"],
            ["2", "Accepted", "Species", "Ericaceae", "Tropical"],
            ["3", "Accepted", "Species", "Polemoniaceae", None],
            ["4", "Synonym", "Species", "Ericaceae", "Tropical"],
            ["5", "Accepted", "Genus", "Ericaceae", "Tropical"],
        ], columns=loader.NAME_COLUMNS)
        self.distributions = pd.DataFrame([
            ["1", "ABT", "0"], ["1", "ABT", "0"], ["1", "ALA", "0"],
            ["2", "ABT", "1"], ["4", "ABT", "0"], ["5", "ABT", "0"],
        ], columns=loader.DISTRIBUTION_COLUMNS)
        self.codes = ["ABT", "ALA", "ANT"]

    def build(self):
        return loader.build_richness(
            self.names, self.distributions, self.codes,
            wikidata_fetcher=lambda names: {},  # no Wikidata data in fixture tests
        )

    def test_native_unique_species_and_global_counts(self):
        result = self.build()
        self.assertEqual(result["Ericaceae"]["sr"], {"ABT": 1, "ALA": 1, "ANT": 0})
        self.assertEqual(result["Ericaceae"]["global"], 2)
        # self.assertEqual(result["Ericaceae"]["climate"], "Temperate")
        self.assertEqual(result["Polemoniaceae"]["sr"], {"ABT": 0, "ALA": 0, "ANT": 0})
        self.assertEqual(result["Polemoniaceae"]["global"], 1)
        # self.assertIsNone(result["Polemoniaceae"]["climate"])
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)
        for family in result.values():
            self.assertTrue(all(type(n) is int and 0 <= n <= family["global"]
                                for n in family["sr"].values()))

    def test_duplicate_names_do_not_inflate_counts(self):
        expected = self.build()
        self.names = pd.concat([self.names, self.names.iloc[[0]]])
        self.assertEqual(self.build(), expected)

    def test_conflicting_species_ids_fail(self):
        other = self.names.iloc[[0]].copy()
        other["family"] = "Polemoniaceae"
        self.names = pd.concat([self.names, other])
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.build()

    def test_unknown_area_fails(self):
        self.distributions.loc[0, "area_code_l3"] = "INVALID"
        with self.assertRaisesRegex(ValueError, "Unknown WGSRPD"):
            self.build()

    def test_region_only_localities_do_not_create_map_areas(self):
        expected = self.build()
        self.distributions = pd.concat([self.distributions, pd.DataFrame(
            [["2", None, "0"], ["2", "", "0"]], columns=loader.DISTRIBUTION_COLUMNS)])
        self.assertEqual(self.build(), expected)

    def test_missing_species_identity_fails(self):
        for column in ["plant_name_id", "family"]:
            with self.subTest(column=column):
                names = self.names.copy()
                names.loc[0, column] = None
                with self.assertRaisesRegex(ValueError, "ID and family"):
                    loader.build_richness(names, self.distributions, self.codes)

    def test_empty_accepted_species_fails(self):
        with self.assertRaisesRegex(ValueError, "No accepted species"):
            loader.build_richness(self.names.iloc[0:0], self.distributions, self.codes)

    def test_order_independence(self):
        self.assertEqual(self.build(), loader.build_richness(
            self.names.iloc[::-1], self.distributions.iloc[::-1], self.codes[::-1],
            wikidata_fetcher=lambda names: {},
        ))

    def test_zip_csv_path_and_map_compatibility(self):
        archive = BytesIO()
        with ZipFile(archive, "w") as zf:
            zf.writestr("wcvp_names.csv", self.names.to_csv(sep="|", index=False))
            zf.writestr("wcvp_distribution.csv", self.distributions.to_csv(sep="|", index=False))
        archive.seek(0)
        self.assertEqual(
            loader.load_archive(archive, self.codes, wikidata_fetcher=lambda names: {}),
            self.build(),
        )
        self.assertTrue(set(self.codes) <= set(loader.map_codes()))


@unittest.skipUnless(os.environ.get("WCVP_ARCHIVE"), "Set WCVP_ARCHIVE for full archive validation")
class ArchiveTests(unittest.TestCase):
    def test_full_archive_contract(self):
        codes = loader.map_codes()
        result = loader.load_archive(os.environ["WCVP_ARCHIVE"], codes)
        self.assertTrue({"Ericaceae", "Polemoniaceae"} <= result.keys())
        json.dumps(result, allow_nan=False)
        for family, record in result.items():
            with self.subTest(family=family):
                self.assertEqual(set(record), {"sr", "global", "climate", "ids", "image"})
                self.assertEqual(set(record["sr"]), set(codes))
                self.assertGreater(record["global"], 0)
                self.assertTrue(all(type(n) is int and 0 <= n <= record["global"]
                                    for n in record["sr"].values()))
                self.assertTrue(record["climate"] is None or isinstance(record["climate"], str))\


if __name__ == "__main__":
    unittest.main()
