#include "ComputerCard.h"
#include <cmath>

class WT : public ComputerCard
{
  constexpr static unsigned tableSize = 512;
  constexpr static uint32_t tableMask = tableSize - 1;

  int16_t sinT[tableSize];

  uint32_t phase;
  uint32_t ph_rot;

public:
  WT()
  {
    phase = 0;

    // Initialize sine table
    for (unsigned i = 0; i < tableSize; i++)
    {
      sinT[i] = int16_t(32000 * sin(2 * i * M_PI / double(tableSize)));
    }
  }

  virtual void ProcessSample()
  {
    // oscillator phase increment
    int32_t knobMain = KnobVal(Main);
    int32_t freqInc = (knobMain * knobMain) << 3;
    phase += freqInc;

    // rotation phase increment
    int32_t knobY = KnobVal(Y) - 2048 << 10;
    ph_rot += knobY;

    // prepare output
    int32_t out[2];
    uint32_t grow = KnobVal(X) << 20;

    yinyang(phase, ph_rot, grow, out);

    AudioOut1(out[0]);
    AudioOut2(out[1]);
  }

protected:
  // common waveforms generator - input Q32 phase -> output Q12 sample
  int32_t __not_in_flash_func(saw)(uint32_t ph)
  {
    return (int32_t)ph >> 20;
  }

  int32_t __not_in_flash_func(tri)(uint32_t ph)
  {

    return (abs((int32_t)ph >> 20) - 1024) << 1;
  }

  int32_t __not_in_flash_func(sqr)(uint32_t ph)
  {
    return (ph & 0x80000000) ? 2047 : -2048;
  }

  // sine lookup, cosine is sine with 0x40000000 phase shift
  int32_t __not_in_flash_func(sine)(uint32_t ph)
  {
    uint32_t index = ph >> 23;        // convert from 32-bit phase to 9-bit lookup table index
    int32_t r = (ph & 0x7FFFFF) >> 7; // fractional part is last 23 bits of phase, shifted to 16-bit
    int32_t s1 = sinT[index];
    int32_t s2 = sinT[(index + 1) & tableMask];
    return (s2 * r + s1 * (65536 - r)) >> 20;
  }

  // Yin-Yang waveform generator
  void __not_in_flash_func(yinyang)(uint32_t ph, int32_t ph_rot, uint32_t grow, int32_t *out)
  {
    // prepare sign and phase for both yin and yang
    int32_t sign = ph >> 31 ? -1 : 1;                                // sign bit
    uint32_t ph_all = (uint32_t)(((uint64_t)(ph * 2) * grow) >> 32); // phase scaled by grow factor

    uint32_t sec = ph_all >> 30; // extract 2 MSB for section
    if (sec == 3)                // 0b11 : eye section, last 1/8 of cycle
    {
      // eye section, single arc
      uint32_t ph_eye = ph_all << 2;
      out[0] = sine(ph_eye * 2) >> 2;
      out[1] = -(sine(ph_eye * 2 + 0x40000000) >> 2) + 1024;
    }
    else
    {
      // body section, 3 parts of 3 arcs
      uint32_t ph_body = (uint32_t)(((uint64_t)ph_all * 0x55555556u) >> 30);
      uint32_t sec_body = ph_body >> 30;
      switch (sec_body)
      {
      case 0:
        out[0] = sine(ph_body * 2) >> 1;
        out[1] = -(sine(ph_body * 2 + 0x40000000) >> 1) + 1024;
        break;
      case 1:
      case 2:
        out[0] = -sine(ph_body - 0x40000000);
        out[1] = sine(ph_body);
        break;
      case 3:
        out[0] = sine(ph_body * 2) >> 1;
        out[1] = (sine(ph_body * 2 + 0x40000000) >> 1) - 1024;
        break;
      }
    }

    int64_t x = sign * out[0];
    int64_t y = sign * out[1];

    // apply rotation
    out[0] = (int32_t)((x * sine(ph_rot) + y * sine(ph_rot + 0x40000000)) >> 12);
    out[1] = (int32_t)((-y * sine(ph_rot) + x * sine(ph_rot + 0x40000000)) >> 12);
  }
};

int main()
{
  set_sys_clock_khz(192000, true);
  WT wt;
  wt.Run();
}
