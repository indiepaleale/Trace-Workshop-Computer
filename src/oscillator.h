#pragma once
#include "ComputerCard.h"
#include <cstdint>
#include <cmath>
#include "lookup_tables.h"

class Oscillator
{
protected:
    // Shared waveform
    int32_t __not_in_flash_func(sine)(uint32_t ph)
    {
        // From ComputerCard sine_wave_lookup example
        uint32_t index = ph >> 23;        // convert from 32-bit phase to 9-bit lookup table index
        int32_t r = (ph & 0x7FFFFF) >> 7; // fractional part is last 23 bits of phase, shifted to 16-bit
        int32_t s1 = SINE_TABLE[index];
        int32_t s2 = SINE_TABLE[(index + 1) & 0x1FF];
        return (s2 * r + s1 * (65536 - r)) >> 20;
    }

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

public:
    // Virtual function to be overridden by derived classes
    virtual void __not_in_flash_func(compute)(uint32_t ph, int32_t mod1, int32_t mod2, int32_t *out) = 0;
    virtual ~Oscillator() = default;
};

class YinYang : public Oscillator
{
public:
    void __not_in_flash_func(compute)(uint32_t ph, int32_t ph_rot, int32_t grow, int32_t *out) override
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