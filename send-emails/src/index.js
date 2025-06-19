export default {
  async fetch(request, env) {
    try {
      const { template, student, professors } = await request.json();

      console.log(`📨 Sending ${professors.length} emails`);

      for (const prof of professors) {
        const personalized = template
          .replace(/{{\s*professor_name\s*}}|{professor_name}/g, prof.last_name)
          .replace(/{{\s*university\s*}}|{university}/g, prof.university)
          .replace(/{{\s*major\s*}}|{major}/g, student.major)
          .replace(/{{\s*student_name\s*}}|{student_name}/g, student.name);

        await fetch("https://api.sendgrid.com/v3/mail/send", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.SENDGRID_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            personalizations: [{
              to: [{ email: prof.email }],
              subject: `Research Opportunity – Inquiry from ${student.name}`
            }],
            from: {
              email: "research@connectnovara.com",
              name: student.name
            },
            reply_to: {
              email: student.email,
              name: student.name
            },
            content: [{
              type: "text/plain",
              value: personalized
            }]
          })
        });
      }

      return new Response("Emails sent");
    } catch (err) {
      return new Response(`Error: ${err.message}`);
    }
  }
};
