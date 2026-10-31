/* libjpeg-turbo 3.2.0's src/jversion.h.in as its CMake build configures it for wasm32-wasip1,
 * with WITH_SIMD=0 and the default libjpeg v6b API (JPEG_LIB_VERSION 62), which Pillow's macOS
 * and Linux wheels also use. It is kept here because the build compiles libjpeg without CMake.
 * Step 37 refuses this file when a line of the template without a placeholder is missing. */

/*
 * jversion.h
 *
 * This file was part of the Independent JPEG Group's software:
 * Copyright (C) 1991-2020, Thomas G. Lane, Guido Vollbeding.
 * libjpeg-turbo Modifications:
 * Copyright (C) 2010, 2012-2026, D. R. Commander.
 * For conditions of distribution and use, see the accompanying README.ijg
 * file.
 *
 * This file contains software version identification.
 */


#if JPEG_LIB_VERSION >= 80

#define JVERSION        "8d  15-Jan-2012"

#elif JPEG_LIB_VERSION >= 70

#define JVERSION        "7  27-Jun-2009"

#else

#define JVERSION        "6b  27-Mar-1998"

#endif

#define JCOPYRIGHT \
  "Copyright (C) 1991-2026 The libjpeg-turbo Project and many others"
