/* Experimental transport for the fixed TC1/T7 ST7735 wiring, SPI mode 0.
 * PORTB writes preserve PB0..PB4; D/C=PB5, MOSI=PB6, SCK=PB7.
 * Writing PINB toggles only the bits written as ones (ATmega324PA manual).
 * No interrupts are masked; this assumes no concurrent PORTB writer.
 */
#if (!defined(BOARD_T7) && !defined(BOARD_TC1)) || !defined(SPI_BITBANG) || defined(LCD_CS) || SPI_MOSI != PB6 || SPI_SCK != PB7 || LCD_DC != PB5
#error Fast display transport requires the TC1/T7 display wiring
#endif
_Static_assert(_SFR_IO_ADDR(SPI_PORT) == _SFR_IO_ADDR(PORTB), "T7 display port");


void LCD_Data2(uint16_t Data)
{
  uint8_t Port = (PORTB & 0x3f) | (1 << PB5);
  uint8_t Bits;
  asm volatile (
    "ldi %[bits],16\n"
    "1: bst %B[data],7\n"
    "bld %[port],6\n"
    "out %[out],%[port]\n"
    "out %[pin],%[clock]\n"
    "lsl %A[data]\n"
    "rol %B[data]\n"
    "out %[pin],%[clock]\n"
    "dec %[bits]\n"
    "brne 1b\n"
    : [data] "+&r" (Data), [port] "+&r" (Port), [bits] "=&d" (Bits)
    : [out] "I" (_SFR_IO_ADDR(PORTB)), [pin] "I" (_SFR_IO_ADDR(PINB)),
      [clock] "r" ((uint8_t)(1 << PB7))
    : "cc", "memory"
  );
}

/* Use the same word timing for erasure and drawing. The first experimental
 * clock-only fill used 62.5 ns low pulses and failed to erase on the T7.
 * Keep one transport path until physical clock timing has been verified.
 */
static void LCD_BackgroundRow(uint16_t Pixels)
{
  while (Pixels--) LCD_Data2(COLOR_BACKGROUND);
}
