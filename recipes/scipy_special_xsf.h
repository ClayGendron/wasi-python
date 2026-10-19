/* For scipy.special's C++ files that include xsf, through recipes/scipy_file_includes.txt (spec
 * 037, Decision 6; Revised at build). xsf defines its functions in headers and marks each
 * XSF_HOST_DEVICE; 453 of them are also `inline`, about forty are not, so two modules that include
 * the same header each define those forty: harmless in two shared objects, a duplicate symbol in
 * one static link. xsf's config.h is read first (it is #pragma once), and XSF_HOST_DEVICE then
 * says `inline`, as the forty should: the linker keeps one copy of each, and nothing computes
 * differently. A doubled `inline` is only a warning, silenced here. */
#include "xsf/config.h"
#undef XSF_HOST_DEVICE
#define XSF_HOST_DEVICE inline
#pragma clang diagnostic ignored "-Wduplicate-decl-specifier"
