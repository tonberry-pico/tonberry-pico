add_library(helix_mp3 STATIC
  mp3dec.c
  mp3tabs.c
  real/buffers.c
  real/bitstream.c
  real/dct32.c
  real/dequant.c
  real/dqchan.c
  real/huffman.c
  real/hufftabs.c
  real/imdct.c
  real/polyphase.c
  real/scalfact.c
  real/stproc.c
  real/subband.c
  real/trigtabs.c
)

target_include_directories(helix_mp3 PUBLIC pub)
#target_compile_options(helix_mp3 PRIVATE -O2 -ffast-math)

target_link_libraries(helix_mp3 PRIVATE pico_platform_compiler pico_platform_sections)
