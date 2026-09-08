# ClearMirror 1.1.1 — PC mic ফোনে পাঠানো

এই সংস্করণে PC-তে লাগানো microphone-এর sound একটি বেছে নেওয়া PC audio output-এ পাঠানো যায়। সেই output থেকে উপযুক্ত audio interface/cable দিয়ে ফোনের **external microphone input**-এ sound নিতে হবে।

**শুধু USB/Wi-Fi screen mirroring চালু করলেই PC mic ফোনে যাবে না।** Android 10, 11, 12, 13 এবং পরের version-এ এই hardware পদ্ধতি ব্যবহার করা যায়, যদি ফোন ও অ্যাপ external mic গ্রহণ করে। সব ফোন, গেম, WhatsApp বা SIM call-এ কাজের নিশ্চয়তা নেই।

## সংযোগ

PC microphone → ClearMirror → আলাদা PC output → উপযুক্ত audio interface/line-to-mic attenuator → ফোনের mic input

- PC-র microphone PC-তেই থাকবে।
- ফোনে 3.5mm headset port থাকলে CTIA microphone input-এর উপযোগী সংযোগ লাগবে। সাধারণ AUX cable বা headphone splitter যথেষ্ট নয়।
- USB-C adapter হলে সেটি **microphone input সমর্থন করে কি না** দেখতে হবে; অনেক adapter শুধু headphone output দেয়।
- PC-র headphone/line output সরাসরি full volume-এ ফোনের mic input-এ দেবেন না। উপযুক্ত interface বা line-to-mic attenuator প্রয়োজন। অ্যাপের volume slider সেই hardware-এর বিকল্প নয়।
- ফোনের USB port audio adapter নিয়ে নিলে screen mirroring-এর জন্য Wi-Fi লাগতে পারে। Android 10-এর Wi-Fi ADB setup প্রথমে USB দিয়ে করতে হয়; Android 11+-এর six-digit wireless pairing Android 10-এ নেই।

## অ্যাপে চালানো

1. `ClearMirror.exe` চালু করুন। **Clear Audio → PC microphone → phone** চাপুন।
2. **PC microphone** থেকে আপনার mic বাছুন।
3. **Output wired to phone** থেকে ফোনে তার দিয়ে লাগানো PC output বাছুন। এখানে ফোনের নাম বাছতে হয় না।
4. গেম/কলের sound শোনার headphone-কে Windows default output রাখুন। ফোনের mic-এ পাঠানোর জন্য আলাদা output ব্যবহার করুন; নইলে অন্য PC sound-ও ফোনে যেতে পারে।
5. Send level 20% ও buffer 60 ms দিয়ে শুরু করুন। **Start PC mic** চাপুন।
6. ফোনের গেম বা calling app-এ mic on করুন। ফোনের mic button PC-র capture নিজে থেকে চালু/বন্ধ করে না; ClearMirror-এর Start/Stop ব্যবহার করুন।

## কাজ করছে কি না পরীক্ষা

ফোনটি PC mic থেকে কিছুটা দূরে রেখে প্রথমে ফোনের voice recorder-এ একটি ছোট test করুন। PC mic-এ কথা বলুন, তারপর ClearMirror-এ **Mute mic output** করে তুলনা করুন। শুধু PC meter নড়লেই ফোন PC mic পাচ্ছে, এমন নয়। এরপর নিজের ব্যবহৃত গেম, WhatsApp এবং প্রয়োজন হলে SIM call আলাদাভাবে পরীক্ষা করুন।

ফোনের built-in mic-ই ব্যবহৃত হলে adapter-এর mic support, CTIA connection এবং সংশ্লিষ্ট অ্যাপের audio route পরীক্ষা করুন। SIM call-এর mic route ফোনভেদে আলাদা হতে পারে।

## নিয়ন্ত্রণ

- **Mute mic output:** ফোনে পাঠানো sound বন্ধ; PC mic capture ও input meter চালু থাকে। Unmute করলে আগের জমা কথা শোনা যাবে না।
- **Stop mic:** PC microphone capture ও output বন্ধ।
- Mic window বন্ধ, mirroring Stop, অথবা ClearMirror বন্ধ করলেও mic বন্ধ হয়।
- Device খুলে ফেললে আবার **Refresh devices** করে বেছে Start করতে হবে। অ্যাপ নিজে থেকে অন্য output-এ পাঠায় না।
- Windows-এ desktop apps-এর microphone permission চালু থাকতে হবে। Crackle হলে buffer 100 ms করুন।

এই feature mic-এর recording file বানায় না এবং network-এ audio পাঠায় না। বিদ্যমান MKV recording-এ PC mic নিজে থেকে mix হয় না। ফোনে audio cable/interface না থাকলে PC mic-এর sound ফোনে পৌঁছাবে না।

## যাচাইয়ের সীমা

ফোনের game mic on করলে game sound বন্ধ হলে, Android 13+ ফোনে mirroring Stop করে **Game mic audio mode (Android 13+)** tick দিয়ে আবার Start করুন। এটি আলাদা playback capture ব্যবহার করে; সব গেম বা call audio-তে কাজের নিশ্চয়তা নেই। কাজ না হলে option বন্ধ করে restart করুন।

সফটওয়্যারের build, audio buffer/mute এবং layout পরীক্ষা করা যায়। আপনার ফোন, adapter এবং প্রতিটি target app-এর test আলাদা করে প্রয়োজন। এই build-এ experimental Android 13+ scrcpy mic injection যুক্ত করা হয়নি।

সূত্র: [Android USB audio](https://source.android.com/docs/core/audio/usb), [scrcpy mic injection proposal](https://github.com/Genymobile/scrcpy/pull/7004)।
