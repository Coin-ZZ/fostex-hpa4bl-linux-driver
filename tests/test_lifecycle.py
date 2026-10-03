"""Execute extracted endpoint/clock/mode functions across probe and prepare.
USB and kernel infrastructure are mocked; this is not hardware validation.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_kernel_logic import function
ROOT=Path(__file__).resolve().parents[1]
HEAD=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
typedef uint64_t u64; typedef uint32_t u32; typedef uint32_t __le32; typedef uint16_t u16; typedef int snd_pcm_format_t;
#define USB_ID(v,p) (((v)<<16)|(p))
#define USB_ID_VENDOR(v) ((v)>>16)
#define USB_DIR_IN 128
#define USB_DIR_OUT 0
#define USB_TYPE_VENDOR 64
#define USB_TYPE_CLASS 32
#define USB_RECIP_INTERFACE 1
#define UAC_VERSION_1 0
#define UAC_VERSION_2 32
#define UAC_VERSION_3 48
#define UAC2_CS_CUR 1
#define UAC2_CS_CONTROL_SAM_FREQ 1
#define UAC2_CS_CONTROL_CLOCK_VALID 2
#define SNDRV_PCM_FORMAT_DSD_U32_BE 52
#define SNDRV_PCM_FMTBIT_DSD_U32_BE (1ULL<<52)
#define QUIRK_FLAG_ITF_USB_DSD_DAC 1
#define QUIRK_FLAG_IGNORE_CLOCK_SOURCE 2
#define QUIRK_FLAG_IFACE_DELAY 4
#define QUIRK_FLAG_SET_IFACE_FIRST 8
#define WARN_ON(x) (x)
#define guard(x) (void)
#define atomic_read(p) (*(p))
#define cpu_to_le32(x) (x)
#define le32_to_cpu(x) (x)
#define usb_audio_dbg(...) ((void)0)
#define usb_audio_err(...) ((void)0)
#define dev_warn(...) ((void)0)
struct usb_device {int dev;}; struct usb_host_interface {int unused;};
struct snd_usb_audio {unsigned int usb_id;u64 quirk_flags;struct usb_device *dev;int mutex;};
struct audioformat {int iface,altsetting,protocol,clock,rate_max;u64 formats;};
struct snd_usb_clock_ref {int rate,locked;bool need_setup;};
struct snd_usb_iface_ref {bool need_setup;};
struct snd_usb_endpoint {struct snd_usb_clock_ref *clock_ref;struct snd_usb_iface_ref *iface_ref;const struct audioformat *cur_audiofmt;int cur_rate,cur_format,ep_num;bool fixed_rate,need_prepare;};
union uac23_clock_source_desc {struct {u32 bmControls;}v2;struct {u32 bmControls;}v3;};
static bool fostex_dsd=true;
static int hardware_rate,mode,applied_mode,write_count,active_count,clock_valid=1,write_error,clock_error,read_error,readback_override;
static int write_length=4,read_length=4,valid_length=1;
static char events[200];static int event_count;
static union uac23_clock_source_desc desc={{7}};static struct usb_host_interface ctrl;
static void ev(char c){events[event_count++]=c;events[event_count]=0;}
static int usb_set_interface(struct usb_device*d,int i,int alt){assert(i==1);if(alt){active_count++;ev('A');}else ev('0');return 0;}
static void msleep(int n){assert(n==20||n==50);}
static int usb_sndctrlpipe(struct usb_device*d,int p){return 0;}
static int usb_rcvctrlpipe(struct usb_device*d,int p){return 0;}
static int snd_usb_ctl_msg(struct usb_device*d,int p,int req,int type,int value,int index,void*data,int len){
 if(type==0x41){assert(req==0&&index==1&&len==0&&data==NULL);mode=value;ev('M');return 0;}
 assert(req==1&&index==0x1000);
 if(value==0x200){ev('V');assert(type==0xa1&&len==1);*(unsigned char*)data=clock_valid;return valid_length;}
 assert(value==0x100&&len==4);
 if(type==0x21){ev('R');write_count++;if(write_error)return write_error;hardware_rate=*(u32*)data;applied_mode=mode;return write_length;}
 assert(type==0xa1);ev('G');if(read_error)return read_error;*(u32*)data=readback_override?readback_override:hardware_rate;return read_length;
}
static struct usb_host_interface *snd_usb_find_ctrl_interface(struct snd_usb_audio*c,int i){return &ctrl;}
static int snd_usb_ctrl_intf(struct usb_host_interface*i){return 0;}
static union uac23_clock_source_desc *snd_usb_find_clock_source(struct snd_usb_audio*c,int clk,const struct audioformat*f){assert(clk==16);return &desc;}
static bool uac_v2v3_control_is_writeable(u32 b,int c){return (b&3)==3;}
#ifndef BASELINE
static bool uac_v2v3_control_is_readable(u32 b,int c){return c==2&&(b&4);}
#endif
static bool uac_clock_source_is_valid(struct snd_usb_audio*c,const struct audioformat*f,int clk){return clock_valid;}
static int snd_usb_clock_find_source(struct snd_usb_audio*c,const struct audioformat*f,bool validate){if(clock_error)return clock_error;return validate&&!clock_valid?-ENXIO:16;}
'''
MID=r'''
static int snd_usb_init_sample_rate(struct snd_usb_audio*c,const struct audioformat*f,int rate){assert(f->protocol==UAC_VERSION_2);return set_sample_rate_v2v3(c,f,rate);}
static int snd_usb_init_pitch(struct snd_usb_audio*c,const struct audioformat*f){return 0;}
static int endpoint_set_interface(struct snd_usb_audio*c,struct snd_usb_endpoint*e,bool active){return usb_set_interface(c->dev,e->cur_audiofmt->iface,active?e->cur_audiofmt->altsetting:0);}
'''
TAIL=r'''
static void reset_counts(void){event_count=write_count=active_count=0;events[0]=0;}
int main(void){
 struct usb_device dev={0};struct snd_usb_audio chip={USB_ID(0x1019,0x0013),0,&dev,0};
 struct audioformat fmt={1,3,UAC_VERSION_2,16,352800,SNDRV_PCM_FMTBIT_DSD_U32_BE|1024};
 struct snd_usb_clock_ref clock={352800,0,true};struct snd_usb_iface_ref iface={true};
 struct snd_usb_endpoint sync={&clock,&iface,&fmt,352800,52,129,false,true};
 /* Actual probe uses snd_usb_init_sample_rate(fp->rate_max), before mode1. */
 hardware_rate=48000;assert(!snd_usb_init_sample_rate(&chip,&fmt,fmt.rate_max));assert(hardware_rate==352800&&applied_mode==0);
 reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==1);
 assert(mode==1&&active_count==1);
#ifdef BASELINE
 assert(write_count==0&&applied_mode==0); /* v0.3 reproduces the missing write. */
#else
 assert(write_count==1&&applied_mode==1);assert(strstr(events,"MRGVA"));
#endif
 /* Data EP shares already-prepared interface: no duplicate mode command. */
 struct snd_usb_endpoint data=sync;data.need_prepare=true;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&data)==1);assert(write_count==0&&event_count==0);
 assert(snd_usb_endpoint_prepare(&chip,&sync)==0);
 /* Lower rate differs from probe baseline, so both versions issue SET_CUR. */
 iface.need_setup=true;clock.need_setup=true;clock.rate=176400;sync.cur_rate=176400;sync.need_prepare=true;
 reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==1);assert(write_count==1&&hardware_rate==176400);
#ifndef BASELINE
 /* Same-rate DSD -> PCM -> DSD, with deliberately warm software clock cache. */
 for(int format=10;format<=52;format+=42){
  iface.need_setup=true;clock.need_setup=false;sync.need_prepare=true;sync.cur_format=format;reset_counts();
  assert(snd_usb_endpoint_prepare(&chip,&sync)==1);assert(write_count==1&&applied_mode==(format==52));
 }
 /* Resume-cleared rate must not re-enter generic GET/SET after strict success. */
 iface.need_setup=true;clock.rate=0;clock.need_setup=false;sync.need_prepare=true;reset_counts();
 assert(snd_usb_endpoint_prepare(&chip,&sync)==1);assert(strstr(events,"MRGVA")&&clock.rate==sync.cur_rate&&!clock.need_setup);
 /* Warm cache must not suppress hardware clock validity checks. */
 iface.need_setup=true;clock.need_setup=false;sync.need_prepare=true;clock_valid=0;reset_counts();
 assert(snd_usb_endpoint_prepare(&chip,&sync)==-ENXIO);assert(active_count==0&&sync.need_prepare&&iface.need_setup);
 clock_valid=1;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==1&&active_count==1);
 /* Readback mismatch and transport failure must fail before active alt. */
 iface.need_setup=true;sync.need_prepare=true;readback_override=48000;reset_counts();
 assert(snd_usb_endpoint_prepare(&chip,&sync)==-EIO&&active_count==0);readback_override=0;
 write_error=-EPIPE;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==-EPIPE&&active_count==0);write_error=0;
 /* Even if copied data happens to equal the rate, a short transfer fails. */
 for(int n=0;n<4;n++){
  iface.need_setup=true;sync.need_prepare=true;write_length=n;reset_counts();
  assert(snd_usb_endpoint_prepare(&chip,&sync)==-EIO&&active_count==0);write_length=4;
  read_length=n;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==-EIO&&active_count==0);read_length=4;
 }
 valid_length=0;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==-EIO&&active_count==0);
 valid_length=-EPIPE;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==-EPIPE&&active_count==0);valid_length=1;
 read_error=-EPIPE;reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==-EPIPE&&active_count==0);read_error=0;
 reset_counts();assert(snd_usb_endpoint_prepare(&chip,&sync)==1&&active_count==1);
#endif
 return 0;
}
'''
class LifecycleTests(unittest.TestCase):
 def run_source(self,root,baseline=False):
  d=Path(root)/'kernel-source/sound/usb';clock=(d/'clock.c').read_text();quirks=(d/'quirks.c').read_text();ep=(d/'endpoint.c').read_text()
  mode=function(quirks,'snd_usb_select_mode_quirk')
  if baseline:mode=mode.replace('snd_pcm_format_t selected_format)', 'snd_pcm_format_t selected_format, unsigned int selected_rate)')
  functions='\n'.join(function(clock,n) for n in ['get_sample_rate_v2v3','snd_usb_set_sample_rate_v2v3','set_sample_rate_v2v3']+([] if baseline else ['snd_usb_fostex_set_rate']))
  prep=function(ep,'snd_usb_endpoint_prepare')
  if baseline:prep=prep.replace('ep->cur_format);','ep->cur_format, ep->cur_rate);')
  source=HEAD+functions+MID+function(quirks,'is_fostex_dsd')+mode+'\n'+ '\n'.join(function(ep,n) for n in ['update_clock_ref_rate','init_sample_rate'])+prep+TAIL
  with tempfile.TemporaryDirectory() as t:
   f=Path(t)/'lifecycle.c';binary=Path(t)/'test';f.write_text(source)
   subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined']+(['-DBASELINE'] if baseline else [])+[str(f),'-o',str(binary)],check=True)
   subprocess.run([str(binary)],check=True)
 def test_current_lifecycle(self):self.run_source(ROOT)
 def test_v03_reproduces_skipped_write(self):self.run_source(ROOT/'tests/fixtures/v0.3',baseline=True)
 def test_probe_max_rate_call_present(self):
  s=(ROOT/'kernel-source/sound/usb/stream.c').read_text();self.assertIn('snd_usb_init_sample_rate(chip, fp, fp->rate_max);',s)
if __name__=='__main__':unittest.main()
