"""Tests unitarios para el parser de campos DGCIBER."""

import unittest
import sys
import os

# Asegurar que el paquete src esté en el path cuando se ejecuta directamente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from speedinform.parser import parse_fields, normalize_nro


class TestNormalizeNro(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize_nro("57 / 2026"), "57/2026")

    def test_no_space(self):
        self.assertEqual(normalize_nro("57/2026"), "57/2026")

    def test_leading_zeros(self):
        self.assertEqual(normalize_nro("007 / 2026"), "7/2026")

    def test_extra_spaces(self):
        self.assertEqual(normalize_nro("  123  /  2025  "), "123/2025")

    def test_single_digit(self):
        self.assertEqual(normalize_nro("1/2024"), "1/2024")


class TestParseFields(unittest.TestCase):
    def test_nro_extraction(self):
        text = "DENUNCIA PENAL DGCIBER - 57 / 2026"
        fields = parse_fields(text)
        self.assertEqual(fields["nro"], "57/2026")

    def test_nro_extraction_no_spaces(self):
        text = "DENUNCIA PENAL DGCIBER - 12/2025"
        fields = parse_fields(text)
        self.assertEqual(fields["nro"], "12/2025")

    def test_c_defaults_to_nn(self):
        text = "Texto sin sección de denunciado"
        fields = parse_fields(text)
        self.assertEqual(fields["c"], "NN")

    def test_fecha_hora_split(self):
        text = "FECHA-HORA-HECHO: 15/03/2026 10:30"
        fields = parse_fields(text)
        self.assertEqual(fields["fecha_hecho"], "15/03/2026")
        self.assertEqual(fields["hora_hecho"], "10:30")

    def test_lugar_extraction(self):
        text = "LUGAR DEL HECHO: Av. Corrientes 1234, CABA"
        fields = parse_fields(text)
        self.assertEqual(fields["lugar"], "Av. Corrientes 1234, CABA")

    def test_fiscal_extraction(self):
        text = "FISCAL INTERVINIENTE: Dr. Juan Pérez"
        fields = parse_fields(text)
        self.assertEqual(fields["fiscal"], "Dr. Juan Pérez")

    def test_empty_text_returns_defaults(self):
        fields = parse_fields("")
        self.assertEqual(fields["c"], "NN")
        self.assertEqual(fields["nro"], "")
        self.assertEqual(fields["relato"], "")

    def test_victima_extraction(self):
        text = (
            "VICTIMA/DAMNIFICADO\n"
            "-APELLIDO Y NOMBRE: GARCIA, CARLOS\n"
            "FECHA-HORA-HECHO: 01/01/2026 08:00\n"
        )
        fields = parse_fields(text)
        self.assertEqual(fields["p"], "GARCIA, CARLOS")

    def test_caratula_extraction(self):
        text = "CARATULA INICIAL: Estafa informática\n"
        fields = parse_fields(text)
        self.assertEqual(fields["s"], "Estafa informática")

    def test_relato_extraction(self):
        text = (
            "CON PLENO CONOCIMIENTO DEL ART. 245 DEL CPP\n"
            "La víctima relata que fue engañada por correo electrónico.\n"
            "INFORMACIÓN QUE SE LE BRINDA A LA VÍCTIMA:"
        )
        fields = parse_fields(text)
        self.assertIn("engañada", fields["relato"])


if __name__ == "__main__":
    unittest.main()
