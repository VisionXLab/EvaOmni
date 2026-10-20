r"""EvaOmni prompt templates.

Fill the question and preformatted options with ``str.format``::

    prompt = PROMPTS["video_audio"].format(
        question="What happens after the person speaks?",
        options="A. The door opens.\nB. The light turns off.",
    )

JSON braces are escaped as ``{{`` and ``}}`` for formatting. Supply the
video, audio, or timestamped ASR transcript separately as model inputs.
The wording and output fields follow the paper; only whitespace is adjusted.
"""


# Audio-only inputs.
AUDIO_ONLY_PROMPT = """\
You are answering a multiple-choice question based ONLY on the Audio provided.
Answer the multiple-choice question and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "audio_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


# Text-only inputs.
TEXT_ONLY_PROMPT = """\
You are answering a multiple-choice question. You DO NOT have access to any video or audio.
Answer using your general knowledge and reasoning only.

Question:
{question}
Options:
{options}

Output:
{{
  "answer": "<single option letter>"
}}
"""


# Video-only inputs.
VIDEO_ONLY_PROMPT = """\
You are answering a multiple-choice question based ONLY on the Video provided.
Answer the multiple-choice question and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "visual_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


# Video+Audio inputs (main benchmark setting).
VIDEO_AUDIO_PROMPT = """\
You are answering a multiple-choice question based on the Video and Audio provided.
Answer the multiple-choice question and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise and minimal as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "visual_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ],
  "audio_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


# ASR-only inputs.
ASR_ONLY_PROMPT = """\
You are answering a multiple-choice question based ONLY on an automatic speech recognition
(ASR) transcript of a video's audio track, with timestamps. Answer the multiple-choice question
and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise and minimal as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "audio_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


# Video+ASR inputs.
VIDEO_ASR_PROMPT = """\
You are answering a multiple-choice question based on the Video and automatic speech
recognition (ASR) transcript of the video's audio track with timestamps provided.
Answer the multiple-choice question and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise and minimal as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "visual_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ],
  "audio_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


PROMPTS = {
    "audio_only": AUDIO_ONLY_PROMPT,
    "text_only": TEXT_ONLY_PROMPT,
    "video_only": VIDEO_ONLY_PROMPT,
    "video_audio": VIDEO_AUDIO_PROMPT,
    "asr_only": ASR_ONLY_PROMPT,
    "video_asr": VIDEO_ASR_PROMPT,
}
