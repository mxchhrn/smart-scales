const fs = require("fs");
const Realm = require("realm");

const DATABASE_ENCRYPTION_KEY = Int8Array.from([
  36, 78, 109, -118, 86, -84, -121, -111, 
  36, 67, 45, -117, 108, -68, -94, -60, 
  36, 78, 109, -118, 86, -84, -121, -111, 
  36, 67, 45, -117, 108, -68, -94, -60, 
  36, 78, 109, -118, 86, -84, -121, -111, 
  36, 67, 45, -117, 108, -68, -94, -60, 
  36, 78, 109, -118, 86, -84, -121, -111, 
  36, 67, 45, -117, 108, -68, -94, -60
]);

const realmPath = process.argv[2];  
 
if (!realmPath) {
  console.error("Give a path to Realm file!");
  process.exit(1);
}

async function exportRealm() {
  const realm = await Realm.open({
    path: realmPath,
    encryptionKey: DATABASE_ENCRYPTION_KEY
  });

  let exportData = {};

  for (const schema of realm.schema) {
    const objects = realm.objects(schema.name);
    exportData[schema.name] = objects.map(obj => Object.assign({}, obj));
  }

  fs.writeFileSync("export.json", JSON.stringify(exportData, null, 2));
  console.log(`Export finished: export.json (from ${realmPath})`);

  realm.close();
  process.exit(0);
}

exportRealm().catch(err => console.error(err));
