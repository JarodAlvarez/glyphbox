# GLYPHBOX

A software-defined fantasy game console. 128×128 pixels, 1-bit monochrome, 5-button input, 2-channel audio, Lua-scripted cartridges.

## Build

```bash
cd glyphbox
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
make -j4
```

## Usage

```bash
./glyphbox path/to/cartridge.gbcart
```

## Tools

- `tools/token-count.py` — count Lua tokens in a source file
- `tools/cart-builder.py` — assemble a `.gbcart` from a game project directory
- `tools/qr-encode.py` — encode a `.gbcart` to a printable card PDF
- `tools/qr-decode.py` — decode a QR card image back to `.gbcart`
