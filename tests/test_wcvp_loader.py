import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
import unittest.mock
from zipfile import ZipFile
import geopandas as gpd
from shapely.geometry import box

import pandas as pd

LOADER = Path(__file__).resolve().parents[1] / "src/data/family-area-sr.json.py"
spec = importlib.util.spec_from_file_location("wcvp_loader", LOADER)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)

# Positions inside each list in the output JSON. These must match the column
# order in the loader (and the index map used in the JS).
#   sr[area]  = [native, introduced, extinct, endemic]
#   global    = [native, introduced, extinct]   (same first three positions)
NATIVE, INTRODUCED, EXTINCT, ENDEMIC = range(4)

# Column order used by the fixtures; build_richness only looks columns up by name.
DIST_COLUMNS = ["plant_name_id", "area_code_l3", "introduced", "extinct"]


def dist_frame(rows):
    """Rows are (plant_name_id, area_code_l3, introduced, extinct)."""
    return pd.DataFrame(rows, columns=DIST_COLUMNS)


class RichnessTests(unittest.TestCase):
    def setUp(self):
        self.names = pd.DataFrame([
            ["1", "Accepted", "Species", "Ericaceae", "temperate"],
            ["2", "Accepted", "Species", "Ericaceae", "tropical"],
            ["3", "Accepted", "Species", "Polemoniaceae", None],
            ["4", "Synonym", "Species", "Ericaceae", "tropical"],
            ["5", "Accepted", "Genus", "Ericaceae", "tropical"],
            ["6", "Accepted", "Species", "Ericaceae", None],
            ["7", "Accepted", "Species", "Ericaceae", None],
        ], columns=loader.NAME_COLUMNS)
        self.distributions = dist_frame([
            ["1", "ABT", "0", "0"], ["1", "ABT", "0", "0"],   # duplicate locality row
            ["1", "ALA", "0", "0"],                           # 1: native, extant, 2 areas
            ["2", "ABT", "0", "0"], ["2", "ANT", "1", "0"],   # 2: native endemic to ABT, introduced in ANT
            ["4", "ABT", "0", "0"],                           # synonym: ignored
            ["5", "ABT", "0", "0"],                           # genus: ignored
            ["6", "ANT", "0", "1"],                           # 6: extinct in its only area
            ["7", "ABT", "0", "0"], ["7", "ALA", "0", "1"],   # 7: extirpated from ALA only
        ])
        # Species 3 (Polemoniaceae) deliberately has no localities at all.
        self.codes = ["ABT", "ALA", "ANT"]

        # LDG
        self.gdf = gpd.GeoDataFrame(
            {"LEVEL3_COD": ["ABT", "ALA", "ANT"]},
            geometry=[
                box(-120, 51, -110, 59),   # ABT -> band 50
                box(-150, 61, -140, 69),   # ALA -> band 60
                box(0, -79, 10, -71),      # ANT -> band -80
            ],
            crs="EPSG:4326",
        )

    def build(self):
        return loader.build_richness(
            self.names, self.distributions, self.codes, self.gdf,
            wikidata_fetcher=lambda names: {},
        )

    def assert_int_list(self, values, length):
        self.assertIsInstance(values, list)
        self.assertEqual(len(values), length)
        self.assertTrue(all(type(n) is int and n >= 0 for n in values), values)

    def test_fixture_columns_match_loader(self):
        self.assertEqual(set(DIST_COLUMNS), set(loader.DISTRIBUTION_COLUMNS))

    def test_counts_by_status_and_global_counts(self):
        result = self.build()
        eri = result["Ericaceae"]
        self.assertEqual(eri["sr"], {
            "ABT": [3, 0, 0, 1],   # species 1, 2, 7 native; species 2 is endemic
            "ALA": [1, 0, 1, 0],   # species 1 native; species 7 extirpated here
            "ANT": [0, 1, 1, 1],   # species 2 introduced; species 6 extinct (and endemic)
        })
        # global: [native, introduced, extinct]
        self.assertEqual(eri["global"], [3, 1, 1])
        self.assertEqual(eri["globalEndemic"], 2)
        self.assertEqual(eri["climate"], {"temperate": 1, "tropical": 1})

        pol = result["Polemoniaceae"]
        self.assertEqual(pol["sr"], {})            # sparse: no localities, no entries
        self.assertEqual(pol["global"], [1, 0, 0])  # no localities -> still counted globally
        self.assertEqual(pol["globalEndemic"], 0)
        self.assertEqual(pol["climate"], {})

        json.dumps(result, allow_nan=False)
        for family in result.values():
            self.assertEqual(set(family),
                             {"sr", "global", "globalEndemic", "climate", "ids", "image", "ldg"})
            self.assertTrue(set(family["sr"]) <= set(self.codes))
            for counts in family["sr"].values():
                self.assert_int_list(counts, 4)
            self.assert_int_list(family["global"], 3)
            self.assertIs(type(family["globalEndemic"]), int)

        # ldg uses the native range, including extinct localities
        ldg = eri["ldg"]
        self.assertEqual(len(ldg), 18)
        self.assertEqual((ldg[50], ldg[60], ldg[-80]), (3, 2, 1))
        self.assertEqual(sum(ldg.values()), 6)
        self.assertEqual(sum(pol["ldg"].values()), 0)

    def test_global_statuses_are_not_additive_with_area_statuses(self):
        eri = self.build()["Ericaceae"]
        accepted = ((self.names.taxon_status == "Accepted") &
                    (self.names.taxon_rank == "Species") &
                    (self.names.family == "Ericaceae")).sum()
        g_native, g_intro, g_ext = eri["global"]
        # Native and extinct partition the species; introduced overlaps with them
        self.assertEqual(g_native + g_ext, accepted)
        self.assertEqual(g_intro, 1)   # species 2 is also counted as native
        # Extinct in one area but alive elsewhere: area extinct counts exceed the global extinct
        self.assertEqual(sum(c[EXTINCT] for c in eri["sr"].values()), 2)
        self.assertEqual(g_ext, 1)

    def test_endemics_are_consistent(self):
        for family, record in self.build().items():
            with self.subTest(family=family):
                self.assertEqual(sum(c[ENDEMIC] for c in record["sr"].values()),
                                 record["globalEndemic"])
                for counts in record["sr"].values():
                    self.assertLessEqual(counts[ENDEMIC], counts[NATIVE] + counts[EXTINCT])

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

    def test_unknown_introduced_area_fails(self):
        # Introduced counts are displayed now, so an unmapped code must not be silently dropped.
        # (Requires the unknown-code check to look at all localities, not just native ones.)
        self.distributions.loc[self.distributions.introduced == "1", "area_code_l3"] = "INVALID"
        with self.assertRaisesRegex(ValueError, "Unknown WGSRPD"):
            self.build()

    def test_region_only_localities_do_not_create_map_areas(self):
        expected = self.build()
        self.distributions = pd.concat([self.distributions, dist_frame(
            [["2", None, "0", "0"], ["2", "", "0", "0"]])])
        self.assertEqual(self.build(), expected)

    def test_missing_species_identity_fails(self):
        for column in ["plant_name_id", "family"]:
            with self.subTest(column=column):
                names = self.names.copy()
                names.loc[0, column] = None
                with self.assertRaisesRegex(ValueError, "ID and family"):
                    loader.build_richness(names, self.distributions, self.codes, self.gdf)

    def test_empty_accepted_species_fails(self):
        with self.assertRaisesRegex(ValueError, "No accepted species"):
            loader.build_richness(self.names.iloc[0:0], self.distributions, self.codes, self.gdf)

    def test_order_independence(self):
        self.assertEqual(self.build(), loader.build_richness(
            self.names.iloc[::-1], self.distributions.iloc[::-1], self.codes[::-1], self.gdf,
            wikidata_fetcher=lambda names: {},
        ))

    def test_zip_csv_path_and_map_compatibility(self):
        archive = BytesIO()
        with ZipFile(archive, "w") as zf:
            zf.writestr("wcvp_names.csv", self.names.to_csv(sep="|", index=False))
            zf.writestr("wcvp_distribution.csv", self.distributions.to_csv(sep="|", index=False))
        archive.seek(0)
        with unittest.mock.patch.object(loader.gpd, "read_file", return_value=self.gdf):
            from_zip = loader.load_archive(archive, self.codes, wikidata_fetcher=lambda names: {})
        self.assertEqual(from_zip, self.build())
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
                self.assertEqual(set(record), {"sr", "global", "globalEndemic",
                                               "climate", "ids", "image", "ldg"})
                # sr is sparse: only areas with at least one record appear
                self.assertTrue(set(record["sr"]) <= set(codes))
                for counts in record["sr"].values():
                    self.assertEqual(len(counts), 4)
                    self.assertTrue(all(type(n) is int and n >= 0 for n in counts))
                self.assertEqual(len(record["global"]), 3)
                self.assertTrue(all(type(n) is int and n >= 0 for n in record["global"]))
                # every accepted species is either native (somewhere extant) or extinct everywhere
                self.assertGreater(record["global"][NATIVE] + record["global"][EXTINCT], 0)
                self.assertEqual(sum(c[ENDEMIC] for c in record["sr"].values()),
                                 record["globalEndemic"])
                self.assertTrue(isinstance(record["climate"], dict))
                self.assertTrue(all(isinstance(v, int) for v in record["climate"].values()))


if __name__ == "__main__":
    unittest.main()