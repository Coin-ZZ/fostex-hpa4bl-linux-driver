"""Execute actual kernel URB construction with mocked feedback; no hardware.
Every outgoing byte is checked independently across wrap and period boundaries.
This does not prove the DAC's interpretation of the emitted byte stream.
"""
from pathlib import Path
import os, re, subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
def extract(s,n):
    m=re.search(r'(?m)^static(?: inline)? (?:void|int|unsigned int) '+n+r'\(',s)
    if not m: raise ValueError(n)
    a=s.index('{',m.start());d=1;b=a+1
    while d:
        d+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[m.start():b]
HEAD=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8; typedef uint32_t __le32;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define unlikely(x) (x)
#define cpu_to_le32(x) (x)
#define SNDRV_PCM_FORMAT_S32_LE 10
#define SNDRV_PCM_FORMAT_DSD_U8 48
#define SNDRV_PCM_FORMAT_DSD_U16_LE 49
#define SNDRV_PCM_FORMAT_DSD_U32_BE 52
#define SNDRV_PCM_STATE_DRAINING 5
#define UAC_FORMAT_TYPE_II 2
#define scoped_guard(kind, lock) for(int once_=1;once_;once_=0)
#define spin_lock_irqsave(lock, flags) do{(flags)=0;}while(0)
#define spin_unlock_irqrestore(lock, flags) ((void)(flags))
struct control{unsigned int appl_ptr;};
struct snd_pcm_runtime{u8 *dma_area;unsigned int period_size,channels,buffer_size,hw_ptr_base;int state,trigger_tstamp;struct control*control;};
struct snd_pcm_substream{struct snd_pcm_runtime*runtime;};
struct audioformat{bool dsd_dop,dsd_bitrev;};
struct snd_usb_endpoint{unsigned int stride,max_urb_frames;int cur_format;};
struct iso_desc{unsigned int offset,length;};
struct urb{void *transfer_buffer,*context;int number_of_packets;unsigned int transfer_buffer_length;struct iso_desc iso_frame_desc[8];};
struct snd_urb_ctx{unsigned int queued,buffer_size;int packets;};
struct snd_usb_substream{
 struct snd_pcm_substream*pcm_substream;struct snd_usb_endpoint*data_endpoint;struct audioformat*cur_audiofmt;
 unsigned int hwptr_done,buffer_bytes,inflight_bytes,transfer_done,frame_limit;
 int lock,fmt_type,last_frame_number,period_elapsed_pending;
 bool lowlatency_playback,tx_length_quirk,running,trigger_tstamp_pending_update;void*dev;
 struct{unsigned int byte_idx,channel,marker;}dsd_dop;
};
static unsigned int rate,phase,notifications;static bool force_empty;
static int snd_usb_endpoint_next_packet_size(struct snd_usb_endpoint*e,struct snd_urb_ctx*c,int i,unsigned int avail){
 if(force_empty) { return -EAGAIN; }
 phase+=rate;int frames=phase/8000;phase%=8000;return frames;
}
static bool snd_usb_endpoint_implicit_feedback_sink(struct snd_usb_endpoint*e){return false;}
static int usb_get_current_frame_number(void*d){return 0;}
static void snd_pcm_gettime(struct snd_pcm_runtime*r,int*t){*t=1;}
static void snd_pcm_period_elapsed(struct snd_pcm_substream*s){notifications++;}
static void snd_pcm_period_elapsed_under_stream_lock(struct snd_pcm_substream*s){notifications++;}
static u8 bitrev8(u8 v){u8 r=0;for(int i=0;i<8;i++){r=(r<<1)|(v&1);v>>=1;}return r;}
'''
TAIL=r'''
/* Distinct byte and channel identities avoid symmetry of 0x69 silence. */
static u8 oracle(unsigned int pos){return (u8)((pos*73+(pos>>3)*19+(pos&4)*31)^(pos>>8));}
static unsigned long long checked;
static void check_rate(unsigned int transport_rate,int format,bool lowlatency){
 enum{RING=4096,OUT=4096};u8 ring[RING],output[OUT];
 for(unsigned int i=0;i<RING;i++)ring[i]=oracle(i);
 struct control ctl={512};
 struct snd_pcm_runtime runtime={.dma_area=ring,.period_size=101,.channels=2,.buffer_size=RING/8,.control=&ctl};
 struct snd_pcm_substream pcm={&runtime};struct snd_usb_endpoint ep={8,180,format};
 struct audioformat fmt={true,true}; /* Format must bypass both DSD transforms. */
 struct snd_usb_substream subs={.pcm_substream=&pcm,.data_endpoint=&ep,.cur_audiofmt=&fmt,
 .hwptr_done=RING-8,.buffer_bytes=RING,.running=true,.lowlatency_playback=lowlatency,.trigger_tstamp_pending_update=true};
 struct snd_urb_ctx ctx={0,OUT,8};struct urb urb={.transfer_buffer=output,.context=&ctx};
 rate=transport_rate;phase=0;force_empty=false;unsigned int wraps=0;
 for(int n=0;n<10000;n++){
  unsigned int old=subs.hwptr_done;ctl.appl_ptr=(old/8+runtime.buffer_size/2)%runtime.buffer_size;
  memset(output,0xcc,sizeof(output));assert(prepare_playback_urb(&subs,&urb,n%2)==0);assert(urb.number_of_packets>0);
  unsigned int sum=0;
  for(int i=0;i<urb.number_of_packets;i++){assert(urb.iso_frame_desc[i].offset==sum);assert(urb.iso_frame_desc[i].length%8==0);sum+=urb.iso_frame_desc[i].length;}
  assert(sum==urb.transfer_buffer_length&&sum==ctx.queued&&sum<=OUT&&sum<RING);
  for(unsigned int i=0;i<sum;i++){assert(output[i]==oracle((old+i)%RING));checked++;}
  for(unsigned int i=sum;i<OUT;i++)assert(output[i]==0xcc);
  assert(subs.hwptr_done==(old+sum)%RING);if(old+sum>=RING)wraps++;
  assert(subs.inflight_bytes==ctx.queued);subs.inflight_bytes-=ctx.queued; /* USB retire outside harness. */
 }
 assert(wraps>100);assert(!subs.trigger_tstamp_pending_update&&runtime.trigger_tstamp==1);
 unsigned int old=subs.hwptr_done;force_empty=true;
 assert(prepare_playback_urb(&subs,&urb,false)==-EAGAIN);assert(subs.hwptr_done==old&&ctx.queued==0);
}
int main(void){
 for(int low=0;low<2;low++){
  check_rate(88200,SNDRV_PCM_FORMAT_DSD_U32_BE,low);check_rate(176400,SNDRV_PCM_FORMAT_DSD_U32_BE,low);
  check_rate(352800,SNDRV_PCM_FORMAT_DSD_U32_BE,low);check_rate(48000,SNDRV_PCM_FORMAT_S32_LE,low);
 }
 assert(notifications>0);printf("Actual URB path: %llu bytes checked; DSD64/128/256, PCM, ring wrap, both latency paths passed\n",checked);return 0;
}
'''
class PayloadPathTests(unittest.TestCase):
    def run_branch(self,branch):
        s=(ROOT/branch/'sound/usb/pcm.c').read_text()
        names=['urb_ctx_queue_advance','fill_playback_urb_dsd_dop','fill_playback_urb_dsd_bitrev','copy_to_urb','copy_to_urb_quirk','prepare_playback_urb']
        code=HEAD+'\n'.join(extract(s,n) for n in names)+TAIL
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'payload.c').write_text(code)
            subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(p/'payload.c'),'-o',str(p/'payload')],check=True)
            subprocess.run([str(p/'payload')],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},check=True)
    def test_ubuntu_actual_urb_path(self): self.run_branch('kernel-source')
    def test_debian_actual_urb_path(self): self.run_branch('kernel-source-debian-6.12')
if __name__=='__main__':unittest.main()
