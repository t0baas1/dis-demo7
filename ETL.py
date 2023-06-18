from psycopg2 import connect, Error
import csv
import pandas as pd

def etl():
    try:
        # Connect to an existing database
        conn = connect(
            host="vsisdb.informatik.uni-hamburg.de",
            database="dis-2023",
            user="vsisp94",
            password="DJC51SUj")
        cursor = conn.cursor()
        
        #Drop tables if they exist
        # print("Dropping existing tables...")
        # cursor.execute(open("drop-tables.sql", encoding="utf-8").read())
        # conn.commit()
        # print("Tables dropped")

        # Execute a command: this creates a new tables
        print("Creating tables")
        cursor.execute(open("stores-and-products.sql", encoding="utf-8").read())
        cursor.execute(open("star-schema.sql", encoding="utf-8").read())
        conn.commit()
        print("Tables created")

        # Execute a command: this loads data into the tables
        print("Loading data...")
        print("Loading shops...")
        cursor.execute("select s.shopid, s.name, ci.name, r.name, co.name"
                       " from shop s"
                        " join city ci on s.cityid = ci.cityid"
                        " join region r on ci.regionid = r.regionid"
                        " join country co on r.countryid = co.countryid")
        shops = cursor.fetchall()
        for s in shops:
            cursor.execute("insert into shopid(id, name, city, region, country)"
                           "values(%s, %s, %s, %s, %s)"
                           "on conflict (id) do nothing",
                           (s[0], s[1], s[2], s[3], s[4]))
            conn.commit()
        
        print("Loading articles...")
        cursor.execute("select a.articleid, a.name, a.price, pg.name, pf.name, pc.name"
                          " from article a"
                            " join productgroup pg on a.productgroupid = pg.productgroupid"
                            " join productfamily pf on pg.productfamilyid = pf.productfamilyid"
                            " join productcategory pc on pf.productcategoryid = pc.productcategoryid")
        articles = cursor.fetchall()
        for a in articles:
            cursor.execute("insert into articleid(id, name, price, productgroup, productfamily, productcategory)"
                           "values(%s, %s, %s, %s, %s, %s)"
                           "on conflict (id) do nothing",
                           (a[0], a[1], a[2], a[3], a[4], a[5]))
            conn.commit()
        
        print("Writing data into DB")
        print("Start writing dates...")
        sales_data = pd.read_csv("sales.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        with open("sales.csv", "r", encoding="latin-1") as f:
            reader = csv.reader(f, delimiter =";")
            # Skip the header row
            next(reader)
            did = 1
            dids = []
            dates = []
            # Iterate over the rows. Check if date already exists in list
            for row in reader:
                if row[0].split(".") not in dates:
                    dids.append(did)
                    dates.append(row[0].split("."))
                    did += 1
            
            # Write dates into DB
            dateids = list(zip(dids,dates))
            for d in dateids:
                cursor.execute("insert into dateid(id, day, month, year)"
                                 "values(%s, %s, %s, %s)"
                                 "on conflict(id) do nothing",
                                 (d[0], d[1][0], d[1][1], d[1][2]))
                conn.commit()
        
        print("Start writing data...")
        #amount = len(open("sales.csv").readlines())
        
        sales_data = pd.read_csv("sales.csv", sep=";", encoding="latin-1", on_bad_lines='skip')
        # with open("sales.csv", "r", encoding="latin-1") as f:
        #     reader = csv.reader(f, delimiter =";")
        #     # Skip the header row
        #     next(reader)
        id = 1
        count = 0
        # Counter for iterating rows
        for row in sales_data.iterrows():
            if count % 1000 == 0:
                print("Writed rows: " + str(count))
            sales_object = row[1]
            # Get the id of the date, check if it exists
            cursor.execute("select id from dateid "
                                " where day = %s "
                                "and month = %s"
                                "and year = %s",
                            (sales_object.Date[:2], sales_object.Date[3:5], sales_object.Date[6:10]))
            did = cursor.fetchone()
            if did:
                did = did[0]
            
            # Get the id of the shop, check if it exists
            cursor.execute("select id from shopid "
                                " where name = %s ",
                                (sales_object.Shop,))
            sid = cursor.fetchone()
            if sid:
                sid = sid[0]
            
            # Get the id of the article, check if it exists
            cursor.execute("select id from articleid "
                                " where name = %s ",
                                (sales_object.Article,))
            aid = cursor.fetchone()
            if aid:
                aid = aid[0]

            # Check for right values in sold and revenue
            try:
                sold = int(sales_object.Sold)
            except ValueError:
                sold = sales_object.Sold
            
            try:
                revenue = float(sales_object.Revenue.replace(",", "."))
            except ValueError:
                revenue = sales_object.Revenue
            
                            # Check for valid data to be present
            if isinstance(did, int) and isinstance(sid, int) and isinstance(aid, int) and isinstance(sold, int) and isinstance(revenue, float):
                cursor.execute("insert into facttable(id, dateid, shopid, articleid, sold, revenue)"
                                "values(%s, %s, %s, %s, %s, %s)"
                                "on conflict(id) do nothing",
                                (id, did, sid, aid, sold, revenue))
                conn.commit()
                id += 1
                count += 1


        cursor.close()
        conn.close()
        return "ETL finished"
    except (Exception, Error) as error:
        return print(error)
    finally:
        #if conn:
         #   cursor.close()
         #   conn.close()
        print("Connection closed")

etl()