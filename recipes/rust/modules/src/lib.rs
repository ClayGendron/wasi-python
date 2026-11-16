//! The one static library of the interpreter's Rust modules. It links each module crate and holds
//! nothing else, so each module's init function reaches the archive that step 60 links.

extern crate _pydantic_core as _;
extern crate orjson as _;
extern crate rust_probe as _;
