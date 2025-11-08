# Shopot File Viewer

Shopot File Viewer is a cross-platform desktop prototype written in Python with Tkinter. The
application can create and open encrypted `.shpt` documents using companion key-array files with the
`.shptk` extension. Documents are decrypted by translating a 10-digit numeric password into a long
key string derived from patterned selections across the 3D key array.

## Features

- **Home hub** to open existing documents, start a new one, or manage key arrays.
- **Document editor** that decrypts `.shpt` files into formatted text, allows edits, and re-encrypts
  content when saving.
- **Key array manager** to generate new 10-layer, 77×77 arrays, browse each layer visually, and
  export them as `.shptk` files.
- **Pattern-based key derivation** that maps each password digit to one of ten selection patterns,
  including fill, checkerboards, stripes, diagonals, and spirals.

## Getting started

1. Ensure Python 3.11+ is installed on macOS or Windows.
2. Install dependencies (standard library only) and launch the GUI:

   ```bash
   python main.py
   ```

3. Use the **Manage key arrays** page to generate or inspect `.shptk` files. Share the resulting key
   file and a 10-digit password with collaborators.
4. Create or open documents from the home page. When prompted, provide the matching `.shptk` file and
   password so the viewer can derive the decryption key.

## File formats

### Key arrays (`.shptk`)

Key arrays are stored as JSON lists with 10 layers. Each layer contains a 77×77 grid filled with
random two-character strings. The array can be regenerated from a shared seed or freshly created from
within the app.

### Documents (`.shpt`)

Documents are JSON objects with version metadata and a salted ciphertext. The ciphertext is produced
by XOR-ing the plaintext with a deterministic keystream derived from the password-generated key
material. While suitable for demonstration purposes, the algorithm is intentionally simple and not
intended for production-grade security.

## Development notes

- Core modules live in the `shopot/` package.
- Patterns for key derivation are defined in `shopot/patterns.py` and can be extended with additional
  selection strategies.
- The GUI is organized into separate pages (`HomePage`, `DocumentEditorPage`, `KeyArrayPage`) managed
  by `ShopotApp`.

Feel free to extend the interface, refine the encryption approach, or integrate richer text editing
features.

## Dependencies

- In order to run this program you will need to have python installed on your `MacOS` or `Windows`
  Device, you can install python from the offical website at `https://www.python.org/`. 3.12 or newer recommended.
