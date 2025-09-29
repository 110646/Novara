export default {
  async fetch(request, env) {
    console.log("Using Postmark API token:", env.POSTMARK_API_TOKEN ? "Loaded" : "Not Found");

    try {
      const { template, student, professors } = await request.json();
      console.log(`Sending ${professors.length} emails`);

      let sentCount = 0;


      function cleanAndFormatTemplate(rawText) {
        const cleanSentences = rawText
          .split(/(?<=[.?!])\s+/) // Split by sentence endings
          .filter(sentence => !sentence.includes("[") && !sentence.includes("]"));

        const paragraphs = [];
        let buffer = [];

        for (const sentence of cleanSentences) {
          buffer.push(sentence);
          if (buffer.length >= 3) {
            paragraphs.push(buffer.join(" "));
            buffer = [];
          }
        }
        if (buffer.length > 0) {
          paragraphs.push(buffer.join(" "));
        }

        return paragraphs.join("\n\n");
      }

      for (const [i, prof] of professors.entries()) {
        console.log(`📤 Sending email ${i + 1} to ${prof.email}`);

        try {
          const cleaned = cleanAndFormatTemplate(template);

          const personalized = cleaned
            .replace(/{{\s*professor_name\s*}}|{\s*professor_name\s*}/g, prof.last_name)
            .replace(/{{\s*university\s*}}|{\s*university\s*}/g, prof.university)
            .replace(/{{\s*major\s*}}|{\s*major\s*}/g, student.major)
            .replace(/{{\s*student_name\s*}}|{\s*student_name\s*}/g, student.name);

          const payload = {
            From: `${student.name} <research@connectnovara.com>`,
            To: prof.email,
            Subject: `Research Opportunity – Inquiry from ${student.name}`,
            TextBody: personalized,
            HtmlBody: personalized.replace(/\n/g, "<br>"),
            ReplyTo: student.email,
            TrackOpens: true,
            Metadata: {
              user_id: String(student.id),
              professor_id: prof.id
            }
          };

          const res = await fetch("https://api.postmarkapp.com/email", {
            method: "POST",
            headers: {
              "Accept": "application/json",
              "Content-Type": "application/json",
              "X-Postmark-Server-Token": env.POSTMARK_API_TOKEN
            },
            body: JSON.stringify(payload)
          });

          console.log(`📬 Postmark response ${res.status} for ${prof.email}`);
          const postmarkData = await res.json().catch(() => ({}));
          const messageId = postmarkData.MessageID || null;

          if (res.status >= 400) {
            console.error("❌ Postmark error:", postmarkData.Message || "Unknown error");
            continue;
          }

          fetch("https://03f72c51c14d.ngrok-free.app/log-sent-email/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: student.id,
              professor_email: prof.email,
              university: prof.university,
              email_body: personalized,
              smtp_id: messageId
            })
          }).catch(err => {
            console.warn("⚠️ Logging failed:", err.message);
          });

          sentCount++;
        } catch (err) {
          console.error(`🔥 Failed to send to ${prof.email}:`, err.message);
          continue;
        }

        // Rate-limit pause
        await new Promise((r) => setTimeout(r, 400));
      }

      console.log(`✅ Finished sending ${sentCount} out of ${professors.length} emails`);
      return new Response("Emails sent and logged (fire-and-forget)");
    } catch (err) {
      console.error("❌ Worker error:", err.message);
      return new Response(`Error: ${err.message}`);
    }
  }
};
